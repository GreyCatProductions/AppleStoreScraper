import os
from fastapi import FastAPI
from schema.shared_state import SharedState
from shared.objects import FailedTask, TaskResult

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")

app = FastAPI()
state = SharedState(csv_path=CSV_PATH)

@app.get("/task")
def get_task():
    url = state.pop_url()
    if url:
        return {"url": url}
    
    return {"Out of urls"}


@app.post("/task/complete")
def complete_task(result: TaskResult):
    if result.similar_apps:
        state.enqueue_new_urls(result.similar_apps)
    state.write_row(result.model_dump())
    return {"status": "ok"}


@app.post("/task/failed")
def failed_task(body: FailedTask):
    state.mark_failed(body.url)
    return {"status": "ok"}


@app.get("/progress")
def stats():
    return {
        "pending": state.get_url_count(),
        "completed": len(state.get_completed_urls()),
        "failed": len(state.get_failed_urls())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
