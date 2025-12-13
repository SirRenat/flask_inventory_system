from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Работает!'

if __name__ == '__main__':
    app.run(debug=True)

#rjl21342134986986joimh
