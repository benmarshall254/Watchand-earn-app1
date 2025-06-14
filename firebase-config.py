import pyrebase

firebase_config = {
    "apiKey": "AIzaSyBIC0u1HfE3aqI-_2aMJT9AKRqUEjlTEJ8",
    "authDomain": "yourproject.firebaseapp.com",
    "projectId": "yourproject",
    "storageBucket": "yourproject.appspot.com",
    "messagingSenderId": "your_sender_id",
    "appId": "your_app_id"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
