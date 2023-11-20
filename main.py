from flask import Flask,request,jsonify
import json
import datetime
from google.cloud import dialogflow_v2beta1 as dialogflow
from google.oauth2 import service_account
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app,resources={r"/*": {"origins": "*"}})
conversations = []
SERVICE_ACCOUNT_FILE = 'quebec-ccai-demo-81db958564a7.json'
project_id='quebec-ccai-demo'
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
@app.get('/conversation/list')
def list_conversation():
    return json.dumps(conversations);

@app.post('/conversation/create')
def create_conversation():
    content = request.json
    response = _create_conversation(project_id,content['conversation_profile_id'])
    conversations.append(response)
    return json.dumps(response)

def _create_conversation(project_id, conversation_profile_id):
    print(project_id)
    print(conversation_profile_id)
    """Creates a conversation with given values

    Args:
        project_id:  The GCP project linked with the conversation.
        conversation_profile_id: The conversation profile id used to create
        conversation."""
    client = dialogflow.ConversationsClient(credentials=credentials)
    conversation_profile_client = dialogflow.ConversationProfilesClient()
    project_path = client.common_project_path(project_id)
    conversation_profile_path = conversation_profile_client.conversation_profile_path(
        project_id, conversation_profile_id
    )
    conversation = {"conversation_profile": conversation_profile_path}
    response = client.create_conversation(
        parent=project_path, conversation=conversation
    )
    print(response)
    print("Life Cycle State: {}".format(response.lifecycle_state))
    print("Conversation Profile Name: {}".format(response.conversation_profile))
    print("Name: {}".format(response.name))
    return response.name

@app.post('/participant/create')
def create_participant():
    content = request.get_json()
    response = _create_participant(project_id,content['conversation_id'],content['role'])
    return json.dumps(response)

def _create_participant(project_id, conversation_id, role):
    """Creates a participant in a given conversation.

    Args:
        project_id: The GCP project linked with the conversation profile.
        conversation_id: Id of the conversation.
        participant: participant to be created."""

    client = dialogflow.ParticipantsClient(credentials=credentials)
    conversation_path = dialogflow.ConversationsClient.conversation_path(
        project_id, conversation_id
    )
    response = client.create_participant(
        parent=conversation_id, participant={"role": role}, timeout=600
    )
    print("Participant Created.")
    print("Role: {}".format(response.role))
    print("Name: {}".format(response.name))

    return response.name

@app.post('/conversation/analyze')
def analyze_content_text():

    if request.form.get('type') == 'text' : 
        message = request.form.get('text')
    else :
        message=request.files.get('blob')
        print(message)
    response = _analyze_content(request.form.get('participant_id'),message,request.form.get('type'))
    return json.dumps(response)
def _analyze_content(participant_id, content,contentType):
    """Analyze text message content from a participant.

    Args:
        project_id: The GCP project linked with the conversation profile.
        conversation_id: Id of the conversation.
        participant_id: Id of the participant.
        text: the text message that participant typed."""
    if contentType == "text": 
        request = dialogflow.StreamingAnalyzeContentRequest(
                text_config= dialogflow.InputTextConfig(language_code="fr-ca"),
                participant=participant_id,
            )
        request2 = dialogflow.StreamingAnalyzeContentRequest(input_text=content)
    else : 
        request=dialogflow.StreamingAnalyzeContentRequest(
            participant=participant_id,
            audio_config=dialogflow.InputAudioConfig(audio_encoding=dialogflow.AudioEncoding.AUDIO_ENCODING_OGG_OPUS,sample_rate_hertz=48000,language_code="fr-ca"))
        bytes = content.read()
        request2=dialogflow.StreamingAnalyzeContentRequest(input_audio=bytes)                                    

    requests = [request,request2]
    client = dialogflow.ParticipantsClient(credentials=credentials)
    def request_generator():
            for request in requests:
                yield request

        # Make the request
    stream = client.streaming_analyze_content(requests=request_generator())
    for response in stream:
        print(response)
        payload = {"text":'',"articles":[]}
    now  = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for agent_response in response.automated_agent_reply.response_messages:
        if agent_response.text:
            print(agent_response)
            payload['text'] = agent_response.text.text[0]
            payload['send_time'] = now
            print(payload)
        if agent_response.payload:
            print(agent_response)
            for richContentResponses in agent_response.payload.get('richContent') :
                for richContentResponse in richContentResponses : 
                    citations = richContentResponse.get('citations')
                    for citation in citations :
                        article = {}
                        article['title'] = citation.get('title')
                        article['snippet']= citation.get('subtitle')
                        article['uri'] = citation.get('actionLink')
                        article['send_time'] = now
                        payload['articles'].append(article)
    return payload
    

@app.post('/conversation/complete')
def complete_conversation():
    content = request.get_json()
    _complete_conversation(project_id,content['conversation_id'])

def _complete_conversation(project_id, conversation_id):
    """Completes the specified conversation. Finished conversations are purged from the database after 30 days.

    Args:
        project_id: The GCP project linked with the conversation.
        conversation_id: Id of the conversation."""

    client = dialogflow.ConversationsClient()
    conversation_path = client.conversation_path(project_id, conversation_id)
    conversation = client.complete_conversation(name=conversation_path)
    print("Completed Conversation.")
    print("Life Cycle State: {}".format(conversation.lifecycle_state))
    print("Conversation Profile Name: {}".format(conversation.conversation_profile))
    print("Name: {}".format(conversation.name))
    return conversation


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))