from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "太牛了，记事本也能写智慧城市后端！"}