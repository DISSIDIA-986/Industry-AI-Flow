import sys

with open("backend/api/cost_estimation_routes.py", "r") as f:
    code = f.read()

# Replace threading with asyncio
code = code.replace("import threading", "import asyncio\nimport threading")
code = code.replace("_service_lock = threading.Lock()", "_service_lock = asyncio.Lock()")

# Replace _get_service
old_get_service = """
def _get_service() -> CostEstimationService:
    global _service
    if _service is not None:
        return _service

    with _service_lock:
        if _service is None:
            _service = CostEstimationService(model_path=_default_model_path())
    return _service
""".strip()

new_get_service = """
async def _get_service() -> CostEstimationService:
    global _service
    if _service is not None:
        return _service

    async with _service_lock:
        if _service is None:
            def _load():
                return CostEstimationService(model_path=_default_model_path())
            _service = await asyncio.to_thread(_load)
    return _service
""".strip()

code = code.replace(old_get_service, new_get_service)

# Health endpoint
old_health = """
@router.get("/health")
async def cost_estimation_health() -> Dict[str, Any]:
    service = _get_service()
""".strip()

new_health = """
@router.get("/health")
async def cost_estimation_health() -> Dict[str, Any]:
    service = await _get_service()
""".strip()

code = code.replace(old_health, new_health)

# Train endpoint
old_train = """
    try:
        result = train_cost_estimation_model(
            dataset_path=dataset_path,
            output_model_path=output_path,
            ridge_alpha=request.ridge_alpha,
            folds=request.folds,
            random_seed=request.random_seed,
        )
    except CostEstimationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("cost estimation training failed")
        raise HTTPException(status_code=500, detail=f"training failed: {exc}") from exc

    service = _get_service()
    service.load(output_path)
""".strip()

new_train = """
    try:
        result = await asyncio.to_thread(
            train_cost_estimation_model,
            dataset_path=dataset_path,
            output_model_path=output_path,
            ridge_alpha=request.ridge_alpha,
            folds=request.folds,
            random_seed=request.random_seed,
        )
    except CostEstimationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("cost estimation training failed")
        raise HTTPException(status_code=500, detail=f"training failed: {exc}") from exc

    service = await _get_service()
    await asyncio.to_thread(service.load, output_path)
""".strip()

code = code.replace(old_train, new_train)

# Predict endpoint
old_predict = """
@router.post("/predict")
async def predict_cost_estimation(request: CostEstimationPredictRequest) -> Dict[str, Any]:
    service = _get_service()
    try:
        prediction = service.predict_project(
            project=request.project.model_dump(),
            confidence_quantile=request.confidence_quantile,
        )
""".strip()

new_predict = """
@router.post("/predict")
async def predict_cost_estimation(request: CostEstimationPredictRequest) -> Dict[str, Any]:
    service = await _get_service()
    try:
        prediction = await asyncio.to_thread(
            service.predict_project,
            project=request.project.model_dump(),
            confidence_quantile=request.confidence_quantile,
        )
""".strip()

code = code.replace(old_predict, new_predict)

# Batch predict endpoint
old_batch = """
@router.post("/predict/batch")
async def batch_predict_cost_estimation(
    request: CostEstimationBatchPredictRequest,
) -> Dict[str, Any]:
    service = _get_service()
    try:
        predictions = service.predict_batch(
            projects=[item.model_dump() for item in request.projects],
            confidence_quantile=request.confidence_quantile,
        )
""".strip()

new_batch = """
@router.post("/predict/batch")
async def batch_predict_cost_estimation(
    request: CostEstimationBatchPredictRequest,
) -> Dict[str, Any]:
    service = await _get_service()
    try:
        predictions = await asyncio.to_thread(
            service.predict_batch,
            projects=[item.model_dump() for item in request.projects],
            confidence_quantile=request.confidence_quantile,
        )
""".strip()

code = code.replace(old_batch, new_batch)

with open("backend/api/cost_estimation_routes.py", "w") as f:
    f.write(code)

print("Done")
