from fastapi import FastAPI
from typing import List
from abcmodel_core.schemas import ModelInput, ModelOutput, SequenceInput
from abcmodel_core.model import ABCParams, evaluate_once

app = FastAPI(title="ABC Model Core v3.0.0 API", version="3.0.0")
params = ABCParams()

@app.get("/")
def root():
    return {"status": "ok", "service": "abc-model-api"}

@app.post("/v1/evaluate", response_model=ModelOutput)
def evaluate(inp: ModelInput):
    out, _ = evaluate_once(inp, params, tr_state={})
    return out

@app.post("/v1/sequence", response_model=List[ModelOutput])
def evaluate_sequence(seq: SequenceInput):
    outputs = []
    tr_state = {}
    for frame in seq.frames:
        out, tr_state = evaluate_once(frame, params, tr_state=tr_state)
        outputs.append(out)
    return outputs