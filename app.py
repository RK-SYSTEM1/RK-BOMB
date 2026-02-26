from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    # সরাসরি মেইন ফোল্ডার থেকে index.html পাঠাবে
    return send_file('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
