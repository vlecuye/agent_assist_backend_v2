from flask import Flask,request,jsonify
import json
import datetime
from google.cloud import dialogflow_v2beta1 as dialogflow
import os
from flask_cors import CORS
import jsonpickle
app = Flask(__name__)
CORS(app,resources={r"/*": {"origins": "*"}})
conversations = []

@app.get('/conversation/list')
def list_conversation():
    return json.dumps(conversations);

@app.post('/conversation/create')
def create_conversation():
    content = request.json
    response = _create_conversation(content['project_id'],content['conversation_profile_id'])
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
    client = dialogflow.ConversationsClient()
    conversation_profile_client = dialogflow.ConversationProfilesClient()
    project_path = client.common_project_path(project_id)
    conversation_profile_path = conversation_profile_client.conversation_profile_path(
        project_id, conversation_profile_id
    )
    conversation = {"conversation_profile": conversation_profile_path}
    response = client.create_conversation(
        parent=project_path, conversation=conversation
    )

    print("Life Cycle State: {}".format(response.lifecycle_state))
    print("Conversation Profile Name: {}".format(response.conversation_profile))
    print("Name: {}".format(response.name))
    return response.name

@app.post('/participant/create')
def create_participant():
    content = request.get_json()
    response = _create_participant(content['project_id'],content['conversation_id'],content['role'])
    return json.dumps(response)

def _create_participant(project_id, conversation_id, role):
    """Creates a participant in a given conversation.

    Args:
        project_id: The GCP project linked with the conversation profile.
        conversation_id: Id of the conversation.
        participant: participant to be created."""

    client = dialogflow.ParticipantsClient()
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
    content = request.get_json()
    response = _analyze_content_text(content['participant_id'],content['text'])
    return json.dumps(response)
def _analyze_content_text(participant_id, text):
    """Analyze text message content from a participant.

    Args:
        project_id: The GCP project linked with the conversation profile.
        conversation_id: Id of the conversation.
        participant_id: Id of the participant.
        text: the text message that participant typed."""

    client = dialogflow.ParticipantsClient()
    text_input = {"text": text, "language_code": "en-US"}
    response = client.analyze_content(
        participant=participant_id, text_input=text_input
    )
    print("AnalyzeContent Response:")
    print("Reply Text: {}".format(response.reply_text))
    print(response)
    payload = {"articles":[],"faqs":[]}
    payload['send_time'] = datetime.datetime.fromtimestamp(response.message.send_time.timestamp()).strftime('%Y-%m-%d %H:%M:%S.%f')
    payload['content'] = response.message.content
    payload['participant_type'] = response.message.participant_role
    for suggestion_result in response.human_agent_suggestion_results:
        if suggestion_result.error is not None:
            print("Error: {}".format(suggestion_result.error.message))
        if suggestion_result.suggest_articles_response:
            for answer in suggestion_result.suggest_articles_response.article_answers:
                payload['articles'].append({"title":answer.title,"uri":answer.uri,"send_time":payload['send_time'],"snippet":answer.snippets[0]})
                print(answer)
                print("Article Suggestion Answer: {}".format(answer.title))
                print("Answer Record: {}".format(answer.answer_record))
        if suggestion_result.suggest_faq_answers_response:
            for answer in suggestion_result.suggest_faq_answers_response.faq_answers:
                print("Faq Answer: {}".format(answer.answer))
                print("Answer Record: {}".format(answer.answer_record))
        if suggestion_result.suggest_smart_replies_response:
            for (
                answer
            ) in suggestion_result.suggest_smart_replies_response.smart_reply_answers:
                print("Smart Reply: {}".format(answer.reply))
                print("Answer Record: {}".format(answer.answer_record))

    for suggestion_result in response.end_user_suggestion_results:
        if suggestion_result.error:
            print("Error: {}".format(suggestion_result.error.message))
        if suggestion_result.suggest_articles_response:
            for answer in suggestion_result.suggest_articles_response.article_answers:
                print("Article Suggestion Answer: {}".format(answer.title))
                print("Answer Record: {}".format(answer.answer_record))
        if suggestion_result.suggest_faq_answers_response:
            for answer in suggestion_result.suggest_faq_answers_response.faq_answers:
                print("Faq Answer: {}".format(answer.answer))
                print("Answer Record: {}".format(answer.answer_record))
        if suggestion_result.suggest_smart_replies_response:
            for (
                answer
            ) in suggestion_result.suggest_smart_replies_response.smart_reply_answers:
                print("Smart Reply: {}".format(answer.reply))
                print("Answer Record: {}".format(answer.answer_record))

    return payload

@app.post('/conversation/complete')
def complete_conversation():
    content = request.get_json()
    _complete_conversation(content['project_id'],content['conversation_id'])

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