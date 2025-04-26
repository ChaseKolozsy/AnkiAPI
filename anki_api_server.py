from flask import Flask
import debugpy

from blueprint_imports import imports
from blueprint_exports import exports
from blueprint_users import users
from blueprint_decks import decks
from blueprint_notetypes import notetypes
from blueprint_cards import cards
from blueprint_study_sessions import study_sessions
from blueprint_db import db

app = Flask(__name__)
app.register_blueprint(imports)
app.register_blueprint(exports)
app.register_blueprint(users)
app.register_blueprint(decks)
app.register_blueprint(notetypes)
app.register_blueprint(cards)
app.register_blueprint(study_sessions)
app.register_blueprint(db)

# Start debugpy on 0.0.0.0:5678 and wait for the debugger to attach
debugpy.listen(("0.0.0.0", 5678))
print("⏳ Waiting for debugger attach on port 5678...")
# Uncomment the next line if you want the server to pause until a debugger attaches:
# debugpy.wait_for_client()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)