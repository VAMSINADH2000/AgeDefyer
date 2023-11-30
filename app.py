import os
from flask import Flask, render_template, request, jsonify,redirect, url_for, session
from langchain import OpenAI, LLMChain, PromptTemplate 
from langchain.memory import ConversationSummaryBufferMemory
from dotenv import find_dotenv, load_dotenv
from antiage import Antiage
from langchain.llms import Replicate
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from medisearch_client import MediSearchClient
import uuid
from functools import wraps
from utils import prompt_template
from functools import wraps
from user import User
import os
from langchain.chat_models import ChatOpenAI

# Intialilizations
antiage = Antiage()
app = Flask(__name__,static_folder='static/')
app.secret_key = os.environ.get('SECRET_KEY') 
os.environ['FLASK_ENV'] = 'production'
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load your env variables
load_dotenv(find_dotenv())

memory = ConversationSummaryBufferMemory(llm = OpenAI(), memory_key="chat_history")
# llama2 = Replicate(model="replicate/llama-2-70b-chat:58d078176e02c219e11eb4da5a02a7830a283b14cf8f94537af893ccff5ee781",
#                   input={"temperature": 0.75, "max_length": 4000, "top_p": 1,"max_new_tokens":1000})

openai = ChatOpenAI(model_name="gpt-4-0613")

client = MongoClient('mongodb+srv://vamsinadh2000:psVlg3Q0JGiEn0eD@agelessaide.cvnocpf.mongodb.net/?retryWrites=true&w=majority')
chat_db = client['chatbot_db']  # You can name your database
conversations = chat_db['conversations']  # Creating a collection to store conversations
papers_collection = chat_db['research_papers']

prompt = PromptTemplate(
    input_variables=["chat_history","user_input"], template=prompt_template
)


chat_chain = LLMChain(
    llm=openai,
    prompt=prompt,
    verbose=True,
    memory=memory,
)

def insert_data(query,bot_response,response_from,db=conversations):
    conversation = {
        "query": query,
        "bot_response": bot_response,
        "response_from": response_from,
        "user_name":session['user']['name'],
        "user_email":session['user']['email']
    }
    db.insert_one(conversation)
    print("Data inserted")

    


# Decorators
def login_required(f):
  @wraps(f)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return f(*args, **kwargs)
    else:
      return redirect('/')
  return wrap

# Routes
@app.route('/user/signup', methods=['POST'])
def signup():
  return User().signup()

@app.route('/user/signout')
def signout():
  print(request.form)
  return User().signout()

@app.route('/user/login', methods=['POST'])
def login():
  return User().login()

@app.route('/skip-login')
def skip_login():
    session['logged_in'] = True
    session['user'] = {'name': 'Guest', 'email': 'guest@example.com'}
    return redirect(url_for('main'))

@app.route('/')
def home():
  return render_template('login.html')



@app.route('/submit_form', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']

    print(f"Name: {name}, Email: {email}, Phone: {phone}")
    return redirect(url_for('index'))

@app.route("/home/")
@login_required
def main():
    return render_template('index.html')
@app.route("/signup/")
def signup_form():
    return render_template('signup.html')
@app.route('/get_papers', methods=['GET'])
def get_papers():
    query = request.args.get('msg')
    papers = antiage.get_papers_response(query)
    if papers is None:
        return {"papers": "None"}
    insert_data(query, papers,"papers",db=papers_collection)
    return jsonify({"papers": papers})

@app.route('/get_response', methods=['POST'])
def get_response():
    query = request.form['msg']
    response = chat_chain.run({"user_input": query})
    response = response.replace('\n','<br/>')
    insert_data(query, response,"GPT4")
    return jsonify({"response": response})

@app.route('/get_research_answer', methods=['GET'])
def get_research_answer():
    query = request.args.get('msg')

    response = antiage.research_response(query,memory=memory, model=openai)
    research_response = response['research_response']
    summary_index = research_response.find('summary')
    formatted_response = research_response[:summary_index] + '<br><strong>' + research_response[summary_index:] + '</strong>'
    insert_data(query, formatted_response,"researcher_papers")
    return jsonify({"research_response": formatted_response})

api_key = "2cfbde1c-e148-47b3-bed5-74c4d5ab35e7"
client = MediSearchClient(api_key=api_key)
@app.route('/medsearch', methods=['POST'])
def medsearch():
    query = request.args.get('msg')
    conversation_id = str(uuid.uuid4())
    responses = client.send_user_message(conversation=[query],
                                         conversation_id=conversation_id,
                                         language="English",
                                         should_stream_response=False)
    response_text = responses[0]['text']
    articles = responses[1]['articles']
    response_text = re.sub(r'\[\d+(?:, \d+)*\]', '', response_text)
    response_text += '<br>'

    for article in articles:
        title = article['title']
        url = article['url']
        authors = ", ".join(article['authors'])
        year = article['year']
        # Adding anchor tags to titles with URLs in the Articles
        response_text += f'<a href="{url}" target="_blank">{title}</a> by {authors}, {year}<br>'
    insert_data(query, response_text,"medisearch")
    
    return {"medsearch": response_text}

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, load_dotenv=True,port=8080)

