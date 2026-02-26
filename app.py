from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    # এটি সরাসরি মেইন ডিরেক্টরি থেকে index.html লোড করবে
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
