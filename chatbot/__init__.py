import langid
from lib.chatterbot.response_selection import get_random_response
from lib.chatterbot.trainers import ChatterBotCorpusTrainer
from website import dao
from website.config import SQLALCHEMY_DATABASE_URI

from chatbot.models import Statement
from chatbot.sentence_similarity import (VietnameseCosineSimilarity,
                                         Word2VecSimilarity)

from .intent_adapter import INTENT_HANDLER
from .mychatbot import MyChatBot

DEFAULT_REPONSE = "Xin lỗi, mình chưa được huấn luyện về vấn đề này."
NOT_VIETNAMESE_LANGUAGE_REPONSE = (
    "Xin lỗi, mình chỉ hiểu tiếng việt. Sorry i can only understand vietnamese."
)

THRESHOLD_UNKNOWN = 0.3


Sonny = MyChatBot(
    "Sonny",
    storage_adapter="chatbot.storage_adapter.MySQLStorageAdapter",
    read_only=True,
    statement_comparison_function=Word2VecSimilarity,
    logic_adapters=[
        {
            "import_path": "chatbot.logic_adapter.MyBestMatch",
            "default_response": DEFAULT_REPONSE,
            "response_selection_method": get_random_response,
        },
        "chatbot.logic_adapter.NameRememberAdapter",
    ],
    database_uri=SQLALCHEMY_DATABASE_URI,
)


def __retrain__():
    trainer = ChatterBotCorpusTrainer(Sonny)
    trainer.train("chatbot/corpus")


def __train__(filePath):
    trainer = ChatterBotCorpusTrainer(Sonny)
    trainer.train(filePath)


def chatbot_reponse(msg: str, oldtag: str = "none", conversation_id=None):
    """
    It takes a message, an old tag, and a conversation id, and returns a response, a tag, and a list of
    next questions

    :param msg: str: The message that the user sent to the chatbot
    :type msg: str
    :param oldtag: The tag of the previous question, defaults to none
    :type oldtag: str (optional)
    :param conversation_id: The id of the conversation
    :return: A dictionary with the keys response, tag, and next_questions.
    """
    # Check message len
    if len(msg) > 255:
        return {"response": "Dài quá!!", "tag": "none", "next_questions": []}

    # Request response to bot
    response_statement = Sonny.get_response(statement=msg, tags=oldtag)
    tag = response_statement.get_tags()
    next_questions = response_statement.get_next_questions()

    if not tag:
        tag = "none"

    # Check if this is an unknown question that chatbot has never learned before
    is_not_known = False
    if response_statement.confidence < THRESHOLD_UNKNOWN:
        response = DEFAULT_REPONSE
        next_questions = dao.get_recommend_questions(tag=oldtag)
        is_not_known = True
        tag = "none"
    else:
        response = response_statement.text

    if is_not_known:
        # Google search this paper if bot does not know about it
        response = google_search_paper(msg)

    #Intent handler
    if response_statement.indent:
        response = INTENT_HANDLER[response_statement.indent]()

    response_data = {"response": response, "tag": tag, "next_questions": next_questions}

    # Store this question to database
    if conversation_id:
        statement_id = None if is_not_known else response_statement.id
        store_question(
            asking=msg,
            answer=response,
            statement_id=statement_id,
            conversation_id=conversation_id,
        )

    return response_data


def store_question(
    asking: str, answer: str, statement_id: int = None, conversation_id: int = None
):
    from website import db

    from .models import Question

    msg_lang = langid.classify(asking)[0]
    if msg_lang in ["vi"]:
        question = Question(
            asking=asking,
            answer=answer,
            statement_id=statement_id,
            conversation_id=conversation_id,
        )
        db.session.add(question)
        db.session.commit()


def google_search_paper(msg: str):
    # Google search this paper if bot does not know about it
    flag_words = [
        "thủ tục",
        "hành chính",
        "giấy tờ",
        "đơn",
        "giấy phép",
        "đăng ký",
        "văn bản",
        "biên bản",
    ]
    # Google search this paper if bot does not know about it
    from pyvi import ViTokenizer

    words = ViTokenizer.tokenize(msg)
    if any(w.replace("_", " ").lower() in flag_words for w in words.split(" ")):
        from googlesearch import search

        # Make a request to google search
        try:
            url = list(
                search(msg, tld="com", lang="vi", num=1, stop=1, pause=2, country="vi")
            )[0]
            reponse = f"{DEFAULT_REPONSE} Nhưng mình nghĩ bạn có thể tham khảo thêm tại đây: {url}"
        except Exception as e:
            reponse = DEFAULT_REPONSE
    else:
        reponse = get_unknow_reponse()
    return reponse


def get_unknow_reponse():
    import random

    unknow_reponses = [
        DEFAULT_REPONSE,
        "Xin lỗi, bạn có thể nói rõ hơn được không?",
        "Xin lỗi, mình vẫn chưa học qua điều này.",
    ]
    return random.choice(unknow_reponses)
