import requests
import os
from PIL import Image
from io import BytesIO
import base64
import re
import json
import calendar
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum, Count
from recycle.models import UploadedFile, Activity
from decouple import config


material_co2_savings = {
    "plastic": 1.02,
    "paper": 0.46,
    "glass": 0.31,
    "metal": 5.86,
    "textile": 3.37,
    "organic": 0.20,
    "e-waste": 2.50,
    "hazardous": 1.00,
    "construction": 0.50,
    "medical": 1.20,
    "mixed": 0.75,
    "rubber": 0.90,
    "wood": 0.40
}
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY')


def generate_recycle_instructions(image_path):
    try:
        image = Image.open(image_path)
        print("Image opened successfully")
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Failed to process image: {e}")
        return None
    API_KEY = OPENROUTER_API_KEY # Remember to remove this from here and add this to the .env file when pushing to github
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Recycling Instructions",
    }
    system_message = """
        You are a recycling assistant. Also ensure to
        determine the cost saved from recycling. If you 
        cannot figure it out from the image, estimate.
        """

    # Build prompt with embedded image
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    # messages.append({
    #     "role": "user",
    #     "content": [
    #         {"type": "text", "text": """
    #          1. Analyze the item in the provided image and provide detailed recycling instructions for it. 
    #          2. Tell me the precise weight of the item in kg
    #          3. Tell me the precise cost saved from recycling it.
    #          4. Give me a recycling location in lagos that accepts the item.
    #          5. Give me a brief description of the item
    #          6. Give me the main material that makes up the item.
             
    #          Note: If recycling this item involves taking it to the recycling location, include this in the recycling instructions
    #          """
    #          },
    #         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
    #     ]
    # }) PREVIOUS PROMPT WITHOUT EXPLCITLY STATING THE OUTPUT FORMAT
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": """
            Analyze the item in the provided image and provide the following information in JSON format:
            - "item_name": The name of the item (string).
            - "recycling_instruction": Detailed recycling instructions (string). Separate distinct steps with a period (.). If the item needs to be taken to a recycling location, include this in the instructions.
            - "item_description": A brief description of the item (string).
            - "item_composition": The main material that makes up the item (string). It must belong to one of the following ["plastic", "paper", "glass", "metal", "textile", "organic", "e-waste", "hazardous", "construction", "medical", "mixed", "rubber", "wood"] so pick one from this that best fits it
            - "item_weight": The precise weight of the item in kg (numerical value, float).
            - "cost_saved": The precise cost saved from recycling in dollars (numerical value, float).
            - "recycling_center_name": The name of a recycling center in Lagos that accepts the item (string).
            - "recycling_location": The location of the recycling center in Lagos (string).
            
            Return only the JSON object (starting with { and ending with }, with no additional text before or after). For example:
            {
                "item_name": "Plastic Bottle",
                "recycling_instruction": "Rinse the bottle thoroughly. Remove the cap. Take to a recycling center.",
                "item_description": "A 500ml clear plastic bottle",
                "item_composition": "Plastic",
                "item_weight": 0.03,
                "cost_saved": 0.05,
                "recycling_center_name": "EcoCycle Lagos",
                "recycling_location": "123 Green Road, Ikeja, Lagos"
            }
            Note: If the item cannot be recycled, just return None
            """
            },
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
        ]
    })

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": messages
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if response.status_code != 200:
            print(f"API request failed with status {response.status_code}: {response.text}")
            return None
        result = response.json()
        
        print("API response from generate_recycle_instruction function:", result['choices'][0]['message']['content'])
        if 'error' in result:
            print(f"API error: {result['error']}")
            return None
        if 'choices' not in result or not result['choices']:
            print(f"Unexpected response format: {result}")
            return None
        if 'null' in result:
            #print('this item cannot be recycled)
            return None
        #print('trying to view the result again ', data['item_composition'])
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    
def information_extractor(text):
    # First check if the output from the generate_recycling_instruction function is correct
    try:
        data = json.loads(text)
        
        required_fields = [
            "item_name", "recycling_instruction", "item_description", "item_composition",
            "item_weight", "cost_saved", "recycling_center_name", "recycling_location"
        ] # Fields required to be in the output
        
        # Check if all required fields are present
        if not all(field in data for field in required_fields):
            print("Missing required fields in JSON:", required_fields)
            raise ValueError("Missing required fields")

        for field in required_fields:
            value = data[field]
            if value is None:
                continue
            if field in ["item_name", "recycling_instruction", "item_description", 
                        "item_composition", "recycling_center_name", "recycling_location"]:
                if not isinstance(value, str):
                    print(f"Field {field} must be a string or null, got {type(value)}")
                    raise ValueError(f"Field {field} must be a string or null")
            elif field in ["item_weight", "cost_saved"]:
                if not isinstance(value, (int, float)):
                    print(f"Field {field} must be a number or null, got {type(value)}")
                    raise ValueError(f"Field {field} must be a number or null")

        # If it passes, it is in the required output
        print("Input text is already in correct JSON format") # Debug print statement
        return data

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Input text is not in correct JSON format or invalid: {e}")
        # Proceed to extract information using an information extractor llm

    # Step 2: If not in correct format, use API to extract information
    API_KEY = OPENROUTER_API_KEY # remember to remove this too

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": f"""
                Extract the relevant information from the text
                    TEXT:{text}
                    """
            },
            {
                "role": "system",
                "content": """
                    You are an expert information extractor. Your output must be strictly valid JSON. Do not include any explanations, headers, or extra text. Always return:
                    {
                    - item_name
                    - recycling_instruction. Separate distinct steps with a period (.)
                    - item_description
                    - item_composition
                    - item_weight in numerical value (in kg)
                    - cost_saved in numerical value (in dollars)
                    - recycling_center_name
                    - recycling_location
                    }
                    If a value is missing or unknown, use `null`. Only return the JSON object and nothing else.
                    Start your response immediately with { and return only the JSON object, no text before or after.
                """
            }
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if response.status_code != 200:
            print(f"API request failed with status {response.status_code}: {response.text}")
            raise ValueError("API request failed")
        
        result = response.json()
        if 'error' in result:
            print(f"API error: {result['error']}")
            raise ValueError("API error")
        if 'choices' not in result or not result['choices']:
            print(f"Unexpected response format: {result}")
            raise ValueError("Unexpected API response format")

        extracted_data = json.loads(result["choices"][0]["message"]["content"])
        return extracted_data

    except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Failed to extract information: {e}")
        raise ValueError(f"Failed to extract information: {str(e)}")
       
    
def generate_similar_items(item_composition, model):
    API_KEY = OPENROUTER_API_KEY # Remember to remove this
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Similar Items",
    }
    system_message = f"You are a recycling assistant. Given the material composition '{item_composition}', provide a list of 4 other recyclable items made from the same material composition. Return the response as a JSON array of strings, e.g., ['Item1', 'Item2', 'Item3', 'Item4']."
    messages = [{"role": "system", "content": system_message}, {"role": "user", "content": "Generate similar items"}]
    data = {"model": model, "messages": messages}
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and result['choices']:
                content = result['choices'][0]['message']['content']
                match = re.search(r'\[.*\]', content, re.DOTALL) 
                if match:
                    return json.loads(match.group(0))
        print(f"API error or unexpected response: {result}")
        return None
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error generating similar items: {e}")
        return None
    

def generate_recycling_report(user):
    uploads = UploadedFile.objects.filter(user=user, status='completed')
    total_items = uploads.count()
    total_weight = sum(upload.item_weight or 0 for upload in uploads)
    total_cost_saved = sum(upload.cost_saved or 0 for upload in uploads)

    # Calculate total carbon offset using the detailed formula
    total_carbon_offset = 0.0
    for item in uploads:
        if item.item_composition and item.item_weight:
            material = item.item_composition.lower().strip()
            if 'cardboard' in material:
                material = 'paper'
            elif 'ceramics' in material:
                material = 'glass'
            elif 'aluminum' in material or 'steel' in material or 'copper' in material:
                material = 'metal'
            co2_per_kg = material_co2_savings.get(material, 0.0) 
            total_carbon_offset += co2_per_kg * item.item_weight

    # Aggregate the item composition for the pie chart
    composition_counts = {}
    for upload in uploads:
        comp = upload.item_composition or 'Unknown'
        composition_counts[comp] = composition_counts.get(comp, 0) + 1

    # Create a PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Recycling Report")
    styles = getSampleStyleSheet()

    # Define the pdf style you want
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    body_style = styles['BodyText']
    list_style = ParagraphStyle(
        name='ListStyle',
        parent=body_style,
        leftIndent=20,
        bulletIndent=10,
        bulletFontSize=10,
    )

    # Now we build the elements of the pdf
    elements = []

    # Title
    elements.append(Paragraph("Recycling Report", title_style))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M WAT')}",
        body_style
    ))
    elements.append(Spacer(1, 12))

    # Summary Statistics
    elements.append(Paragraph("Summary Statistics", subtitle_style))
    summary_items = [
        f"Total Items Recycled: {total_items}",
        f"Total Weight Recycled: {total_weight:.2f} kg",
        f"Estimated Carbon Offset: {total_carbon_offset:.2f} kg CO2e",
        f"Total Cost Savings: ${total_cost_saved:.2f}",
    ]
    summary_list = ListFlowable(
        [ListItem(Paragraph(item, body_style), bulletText="•") for item in summary_items],
        bulletType='bullet',
        start='bulletchar',
    )
    elements.append(summary_list)
    elements.append(Spacer(1, 12))

    # Pie Chart Data
    elements.append(Paragraph("Pie Chart Data", subtitle_style))
    elements.append(Paragraph(
        "The following data represents the distribution of items by material composition, suitable for a pie chart:",
        body_style
    ))
    pie_data_items = [
        f"{comp}: {count} items ({(count / total_items * 100):.1f}%{')' if total_items else ''}"
        for comp, count in composition_counts.items()
    ]
    pie_list = ListFlowable(
        [ListItem(Paragraph(item, list_style), bulletText="•") for item in pie_data_items],
        bulletType='bullet',
        start='bulletchar',
    )
    elements.append(pie_list)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Note: A pie chart can be generated using this data with a tool like Matplotlib or another charting library.",
        body_style
    ))
    elements.append(Spacer(1, 12))

    # Recommendations
    elements.append(Paragraph("Recommendations", subtitle_style))
    elements.append(Paragraph(
        "Consider integrating a charting tool to visualize the pie chart data in future reports. "
        "The carbon offset is calculated using material-specific CO2 savings per kg.",
        body_style
    ))

    # Build the PDF
    doc.build(elements)

    # Log the activity after successful PDF generation
    Activity.objects.create(
        user=user,
        activity_type='export',
        title='Report Exported',
        timestamp=timezone.now(),
        meta=user.username
    )

    # Reset buffer position to the beginning
    buffer.seek(0)
    return buffer


def generate_recycling_instructions_pdf(upload):
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"Recycling Instructions - {upload.item_name}")
    styles = getSampleStyleSheet()

    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    body_style = styles['BodyText']
    list_style = ParagraphStyle(
        name='ListStyle',
        parent=body_style,
        leftIndent=20,
        bulletIndent=10,
        bulletFontSize=10,
    )


    elements = []


    elements.append(Paragraph(f"Recycling Instructions for {upload.item_name or 'Item'}", title_style))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M WAT')}",
        body_style
    ))
    elements.append(Spacer(1, 12))


    elements.append(Paragraph("Item Details", subtitle_style))
    details_items = [
        f"Item Name: {upload.item_name or 'Unknown'}",
        f"Description: {upload.item_description or 'No description available'}",
        f"Composition: {upload.item_composition or 'Unknown'}",
        f"Weight: {upload.item_weight:.2f} kg" if upload.item_weight is not None else "Weight: Unknown",
    ]
    details_list = ListFlowable(
        [ListItem(Paragraph(item, body_style), bulletText="•") for item in details_items],
        bulletType='bullet',
        start='bulletchar',
    )
    elements.append(details_list)
    elements.append(Spacer(1, 12))
    print(upload.file)

    if upload.file and hasattr(upload.file, 'path') and os.path.exists(upload.file.path):
        try:
            img = ReportLabImage(upload.file.path, width=200, height=200) 
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception as e:
            print(f"Failed to load image: {e}")


    elements.append(Paragraph("Recycling Instructions", subtitle_style))
    if upload.recycling_instructions:
        steps = [step.strip() for step in upload.recycling_instructions.split('.')]
        steps = [step for step in steps if step]  
        if steps:
            instructions_list = ListFlowable(
                [ListItem(Paragraph(step, list_style), bulletText="•") for step in steps],
                bulletType='bullet',
                start='bulletchar',
            )
            elements.append(instructions_list)
        else:
            elements.append(Paragraph("No specific instructions available.", body_style))
    else:
        elements.append(Paragraph("No instructions provided.", body_style))
    elements.append(Spacer(1, 12))


    elements.append(Paragraph("Recycling Center Information", subtitle_style))
    center_items = [
        f"Center Name: {upload.recycling_center_name or 'Unknown'}",
        f"Location: {upload.recycling_location or 'Unknown'}",
    ]
    center_list = ListFlowable(
        [ListItem(Paragraph(item, body_style), bulletText="•") for item in center_items],
        bulletType='bullet',
        start='bulletchar',
    )
    elements.append(center_list)
    elements.append(Spacer(1, 12))


    doc.build(elements)


    Activity.objects.create(
        user=upload.user,
        activity_type='download',
        title='Recycling Instructions Downloaded',
        timestamp=timezone.now(),
        meta=f"Item: {upload.item_name or 'Unknown'}"
    )


    buffer.seek(0)
    return buffer

def home_view_details(recycled_items):
    details = {}
    
    # Calculate total cost saved and total weight
    totals = recycled_items.aggregate(
        total_cost_saved=Sum('cost_saved'),
        total_weight=Sum('item_weight')
    )
    total_cost_saved = totals['total_cost_saved'] or 0.0
    total_weight = totals['total_weight'] or 0.0
    
    # Calculate total carbon offset
    # CO2 savings per kg based on material type (from recyclewits.com, 2023)
    total_carbon_offset = 0.0
    for item in recycled_items:
        if item.item_composition and item.item_weight:
            # Normalize material name (lowercase, strip spaces)
            material = item.item_composition.lower().strip()
            # Map similar materials (e.g., "cardboard" to "paper")
            if 'cardboard' in material:
                material = 'paper'
            elif 'ceramics' in material:
                material = 'glass'
            elif 'aluminum' in material or 'steel' in material or 'copper' in material:
                material = 'metal'
            # Calculate carbon offset for this item
            co2_per_kg = material_co2_savings.get(material, 0.0)  # Default to 0 if material not found
            total_carbon_offset += co2_per_kg * item.item_weight
    # Waste breakdown for pie chart (by item_composition)
    waste_breakdown = recycled_items.values('item_composition').annotate(
        count=Count('id'),
        total_weight=Sum('item_weight')
    ).exclude(item_composition__isnull=True).exclude(item_composition='')
    
    # Prepare data for pie chart
    labels = []
    weights = []
    for entry in waste_breakdown:
        composition = entry['item_composition']
        # Normalize labels (e.g., map "cardboard" to "paper")
        if 'cardboard' in composition.lower():
            composition = 'Paper'
        elif 'aluminum' in composition.lower() or 'steel' in composition.lower() or 'copper' in composition.lower():
            composition = 'Metal'
        else:
            composition = composition.capitalize()
        labels.append(composition)
        weights.append(float(entry['total_weight']))
        
    # Calendar data
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day

    # Get the first day of the month and the number of days in the month
    cal = calendar.monthcalendar(year, month)
    month_name = today.strftime('%B')  # e.g., "May"
    weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

    # Prepare calendar days with metadata
    calendar_days = []
    for week in cal:
        for i, cal_day in enumerate(week):
            if cal_day == 0:  # Days from previous/next month
                calendar_days.append({
                    'day': '',  # Empty for display
                    'class': 'other-month',
                    'has_event': False
                })
            else:
                # Check if this day is today
                is_today = (cal_day == day)
                # Placeholder for events (you can integrate real events from your database)
                has_event = cal_day in []  # Example event days
                calendar_days.append({
                    'day': cal_day,
                    'class': 'today' if is_today else '',
                    'has_event': has_event
                })
    details['total_cost_saved'] = total_cost_saved
    details['total_weight'] = total_weight
    details['total_carbon_offset'] = total_carbon_offset
    details['recycled_items'] = recycled_items
    details['labels'] = labels
    details['weights'] = weights
    details['month_name'] = month_name
    details['year'] = year
    details['weekdays'] = weekdays
    details['calendar_days'] = calendar_days
    details['month'] = month
    
    return details
                    