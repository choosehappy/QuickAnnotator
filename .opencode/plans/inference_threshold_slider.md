# Inference Threshold Slider Feature Plan

## Overview

Add a UI slider to control the inference threshold (currently hardcoded as `constants.INFERENCE_THRESHOLD = 0.5`). The threshold will be stored in the DLActor Ray actor state, passed into `train_pred_loop`, and used in `run_inference` → `postprocess_output`.

---

## 1. Backend: Store threshold in DLActor state

**File:** `quickannotator/dl/ray_jackson.py`

- Add `self.inference_threshold: float = 0.5` to `DLActor.__init__` (use default from constants)
- Add getter:
  ```python
  def get_inference_threshold(self) -> float:
      return self.inference_threshold
  ```
- Add setter:
  ```python
  def set_inference_threshold(self, threshold: float) -> float:
      self.inference_threshold = threshold
      return self.inference_threshold
  ```
- Add `inference_threshold` to `get_detailed_state()` return dict

---

## 2. Backend: Pass threshold into `train_pred_loop` and `run_inference`

**File:** `quickannotator/dl/training.py`

- In `train_pred_loop`, read threshold from actor:
  ```python
  inference_threshold = ray.get(myactor.get_inference_threshold.remote())
  ```
- Pass `inference_threshold` to `run_inference()` call on line 224:
  ```python
  run_inference(device, model, tiles, inference_threshold)
  ```

**File:** `quickannotator/dl/inference.py`

- Update `run_inference` signature:
  ```python
  def run_inference(device, model, tiles, inference_threshold: float):
  ```
- Pass `inference_threshold` into `postprocess_output()`:
  ```python
  polygons = postprocess_output(pred, inference_threshold)
  ```
- Update `postprocess_output` signature:
  ```python
  def postprocess_output(outputs, min_area=100, dilate_kernel=2, inference_threshold: float = None):
  ```
- Replace the hardcoded reference `constants.INFERENCE_THRESHOLD` on line 64 with the parameter `inference_threshold` (fall back to `constants.INFERENCE_THRESHOLD` if `None`)

---

## 3. Backend: New API endpoint for setting threshold

**File:** `quickannotator/api/v1/ray/models.py`

- Add schema:
  ```python
  class SetInferenceThresholdArgsSchema(Schema):
      threshold = fields.Float(required=True, description="Inference threshold value between 0 and 1.")
  ```

**File:** `quickannotator/api/v1/ray/routes.py`

- Add new route class `SetInferenceThresholdResource`:
  ```python
  @bp.route('/train/threshold/<string:annotation_class_id>', endpoint='set_inference_threshold')
  class SetInferenceThresholdResource(MethodView):
      @bp.arguments(server_models.SetInferenceThresholdArgsSchema, location='query')
      @bp.response(200, server_models.GetDLActorStatusResponseSchema)
      @bp.alt_response(404, schema=error_handler.ErrorSchema)
      @bp.alt_response(408, schema=error_handler.ErrorSchema)
      def post(self, args, annotation_class_id):
          actor_name = build_actor_name(int(annotation_class_id))
          try:
              actor = ray.get_actor(actor_name)
          except ValueError:
              return abort(404)
          except ray.exceptions.GetTimeoutError:
              return abort(408)
          
          ref = actor.set_inference_threshold.remote(args['threshold'])
          try:
              ray.get(ref, timeout=constants.RAY_GET_TIMEOUT)
          except ray.exceptions.GetTimeoutError:
              return abort(408)
          
          # Reset all PROCESSING tiles so new threshold applies on next inference pass
          try:
              actor.reset_all_processing_tiles.remote()
          except Exception:
              pass
          
          try:
              detailed_state = ray.get(actor.get_detailed_state.remote(), timeout=constants.RAY_GET_TIMEOUT)
              return detailed_state, 200
          except ray.exceptions.GetTimeoutError:
              return abort(408)
  ```

**File:** `quickannotator/db/crud/tile.py`

- The `reset_all_PROCESSING_tiles` method already exists on line 280. We need a Ray-actor-callable wrapper. Add to `DLActor` in `ray_jackson.py`:
  ```python
  def reset_all_processing_tiles(self):
      tilestore = TileStoreFactory.get_tilestore()
      tilestore.reset_all_PROCESSING_tiles(self.annotation_class_id)
  ```

---

## 4. Frontend: API helper

**File:** `quickannotator/client/src/helpers/api.ts`

- Add fetch function:
  ```typescript
  export const setInferenceThreshold = async (annotation_class_id: number, threshold: number): Promise<{ data: DLActorStatus, status: number }> => {
      const query = new URLSearchParams({ threshold: threshold.toString() });
      return await post<null, DLActorStatus>(`/ray/train/threshold/${annotation_class_id}?${query}`, null);
  };
  ```

---

## 5. Frontend: Threshold slider component in ClassesPane

**File:** `quickannotator/client/src/components/classesPane.tsx`

### State additions

- Add `inferenceThreshold` state:
  ```typescript
  const [inferenceThreshold, setInferenceThreshold] = useState(0.5);
  const [showSlider, setShowSlider] = useState(false);
  const sliderRef = useRef<HTMLDivElement>(null);
  ```

### Hover behavior

- Wrap the threshold display + slider in a container with `onMouseEnter` / `onMouseLeave` handlers
- On mouse enter: `setShowSlider(true)`
- On mouse leave: `setShowSlider(false)`, then call `setInferenceThreshold` endpoint if value changed

### UI placement

- In the `ClassesPane` render, next to the `TrainingStatusButton` (around line 104-108), add a threshold icon + value:
  ```tsx
  <div 
    ref={sliderRef}
    onMouseEnter={() => setShowSlider(true)}
    onMouseLeave={() => {
        setShowSlider(false);
        // commit value if changed
        if (inferenceThreshold !== defaultThreshold) {
            setInferenceThreshold(props.currentAnnotationClass?.id, inferenceThreshold);
        }
    }}
    style={{ position: 'relative', display: 'inline-block' }}
  >
      <Button variant="outline-secondary" size="sm" className="ms-1">
          <TargetIcon /> {inferenceThreshold.toFixed(2)}
      </Button>
      {showSlider && (
          <div style={{ position: 'absolute', top: '100%', left: 0, zIndex: 20, backgroundColor: 'white', padding: 8, borderRadius: 4, boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
              <input 
                  type="range" 
                  min="0.01" 
                  max="0.99" 
                  step="0.01" 
                  value={inferenceThreshold}
                  onChange={(e) => setInferenceThreshold(parseFloat(e.target.value))}
              />
              <span>{inferenceThreshold.toFixed(2)}</span>
          </div>
      )}
  </div>
  ```

### Props update

- Add to `ClassesPane` interface:
  ```typescript
  inferenceThreshold: number;
  setInferenceThreshold: (threshold: number) => void;
  ```
- Pass from `annotationPage.tsx` (lift `inferenceThreshold` state up or keep local to `ClassesPane`)

### Note on state lifting

The simplest approach: keep `inferenceThreshold` state local to `ClassesPane`. On hover-away, POST the new value. The `DLActorStatus` response from the endpoint does not need to include the threshold in the current schema — we can extend `GetDLActorStatusResponseSchema` later if we want to sync back.

---

## 6. Frontend: Wire threshold into annotationPage.tsx

**File:** `quickannotator/client/src/routes/annotationPage.tsx`

- Add state for `inferenceThreshold` (if not kept local to ClassesPane):
  ```typescript
  const [inferenceThreshold, setInferenceThreshold] = useState(0.5);
  ```
- Pass as prop to `ClassesPane` on line 278-280

---

## File change summary

| File | Change |
|------|--------|
| `quickannotator/constants.py` | No change (keep as fallback default) |
| `quickannotator/dl/ray_jackson.py` | Add `inference_threshold` attr, getter, setter, `reset_all_processing_tiles` method, include in `get_detailed_state` |
| `quickannotator/dl/training.py` | Read threshold from actor, pass to `run_inference()` |
| `quickannotator/dl/inference.py` | Add `inference_threshold` param to `run_inference()` and `postprocess_output()`, use it instead of `constants.INFERENCE_THRESHOLD` |
| `quickannotator/api/v1/ray/models.py` | Add `SetInferenceThresholdArgsSchema` |
| `quickannotator/api/v1/ray/routes.py` | Add `SetInferenceThresholdResource` endpoint |
| `quickannotator/db/crud/tile.py` | No change (uses existing `reset_all_PROCESSING_tiles`) |
| `quickannotator/client/src/helpers/api.ts` | Add `setInferenceThreshold` API helper |
| `quickannotator/client/src/components/classesPane.tsx` | Add threshold icon, slider, hover show/hide, commit on mouse leave |
| `quickannotator/client/src/routes/annotationPage.tsx` | Pass `inferenceThreshold` state to `ClassesPane` |
