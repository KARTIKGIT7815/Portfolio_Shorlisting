from flask import Flask,render_template,request
from PyPDF2 import PdfReader
import chromadb
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import json


app = Flask(__name__)
client = chromadb.Client()


llm = ChatGroq(
    model="gemma2-9b-it",
    temperature=0.5,
    timeout=None,
    max_retries=2,
    api_key='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'
)

@app.route('/')
def home():
    return render_template('Page1.html')

@app.route('/upload', methods=['POST'])
def upload():
    
    #Taking Information from pdf and stored in Database
    uploaded_files = request.files.getlist('pdf_files')

    collection = client.get_or_create_collection(name="resume_collection")

    all_texts = []

    for pdf_file in uploaded_files:
        reader = PdfReader(pdf_file)
        text = ""
        
        # Extract text from all pages
        for page in reader.pages:
            text += page.extract_text()
        
        person_id = pdf_file.filename.replace(".pdf", "").replace("_", " ")
        
        # Add document and ID to the collection
        collection.add(
            documents=[text.strip()],
            ids=[person_id]
        )
        all_texts.append(text.strip())

    #---------------------------------------------------------------------------------------------

    #Taking Job Requirements From the Company
    job_post = request.form.get('words', '')
    students = int(request.form.get('students', 0))

    #Prompt For Filtering the Information
    prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    '''You have to extract following details from provided job post. Extract JOB_ROLE, EXPERIENCE, 
                    SKILLS in json format  extract only the curly bracket information. Dont provide preamble
                     information''',
                ),
                ("human", "{input}"),
            ]
        )

    chain = prompt | llm
    result = chain.invoke(
            {
                "input": job_post,
            }
        )

    try:
        # Parse the LLM response as JSON
        Details = json.loads(result.content)
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return "Error: Could not process job post details. Please check the input and try again."

    SE = ' '.join([' '.join(Details['SKILLS']), ' '.join(Details['EXPERIENCE'])])
    print(SE)
    #Query to find required Matchings
    results = collection.query(
        query_texts=[SE], 
        n_results=students 
        )


    #To join the Required Information
    portfolios = ''.join(results['documents'][0])
    portfolios
    
    #------------------------------------------------------------------------------------------------------------------------

    #Email Prompt
    company_name = request.form.get('company_name')
    consultancy_name = request.form.get('consultancy_name')

    email_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f'''We are working as a placement officer in placement consultancy {consultancy_name}.
                We have short-listed candidates' portfolios as per the requirement of {company_name}'s job post.
                Create an email to the recruitment team of {company_name} mentioning that we have the best suitable candidates for your job post
                after Best Regards only the company name and consultancy name should be seen.
                Do not provide preamble,.''',
            ),
            ("human", "{input}"),
        ]
    )

    email_chain = email_prompt | llm
    result_email = email_chain.invoke(
        {
            "input": portfolios,
        }
    )

    Out =  result_email.content
    return render_template('Page2.html',Email=Out)

if __name__ == '__main__':
    app.run(debug=True)
