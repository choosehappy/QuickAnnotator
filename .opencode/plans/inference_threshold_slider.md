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

**File:** `quickannotator/api/v1/ray/models.py`

- Extend `GetDLActorStatusResponseSchema` to include `inference_threshold`:
  ```python
  inference_threshold = fields.Float(
      load_default=None,
      description="Current inference threshold value, or null if actor is not ready."
  )
  ```

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

- Add import:
  ```python
  from quickannotator.db.crud.tile import TileStoreFactory
  ```

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
              tilestore = TileStoreFactory.get_tilestore()
              tilestore.reset_all_PROCESSING_tiles(int(annotation_class_id))
          except Exception:
              pass
          
          try:
              detailed_state = ray.get(actor.get_detailed_state.remote(), timeout=constants.RAY_GET_TIMEOUT)
              return detailed_state, 200
          except ray.exceptions.GetTimeoutError:
              return abort(408)
  ```

**File:** `quickannotator/db/crud/tile.py`

- No change needed — the `reset_all_PROCESSING_tiles` method already exists on line 280.
  The route calls it directly on the TileStore instead of through an actor wrapper.

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

**File:** `quickannotator/client/src/types.ts`

- Extend `DLActorStatus` interface:
  ```typescript
  export interface DLActorStatus {
      annotation_class_id: number;
      enable_training: boolean;
      allow_pred: boolean;
      proc_running_since: string | null;
      inference_threshold: number | null;  // NEW
  }
  ```

---

## 5. Frontend: Threshold slider component in ClassesPane

**File:** `quickannotator/client/src/components/classesPane.tsx`

### Imports update

- Add `useRef` to the React imports (only `useState` is currently imported):
  ```typescript
  import { useState, useRef } from 'react';
  ```
- Add `Target` to the `react-bootstrap-icons` import:
  ```typescript
  import { Plus, Pencil, Trash, Target } from 'react-bootstrap-icons';
  ```

### State additions

- Add state for slider control:
  ```typescript
  const [inferenceThreshold, setInferenceThreshold] = useState<number | null>(null);
  const [showSlider, setShowSlider] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [sliderValue, setSliderValue] = useState(0.5);
  const sliderRef = useRef<HTMLDivElement>(null);
  ```

- `inferenceThreshold` is `null` until the detailed actor state includes a threshold value (slider inactive).
- `sliderValue` tracks the live slider position independently of the committed `inferenceThreshold`.

### Slider activation

- The slider is **inactive** (disabled) until the `GetDLActorStatusResponseSchema` response includes a non-null `inference_threshold`.
- Once `inferenceThreshold` is non-null, the slider icon renders the value and becomes hoverable.
- On hover in: `setShowSlider(true)` and `setSliderValue(inferenceThreshold)`.
- On hover out: if `sliderValue` differs from `inferenceThreshold`, POST the new value.

### Hover behavior + save flow

- On mouse leave:
  ```typescript
  onMouseLeave={() => {
      setShowSlider(false);
      if (Math.abs(sliderValue - inferenceThreshold) > 0.001) {
          handleSaveThreshold(sliderValue);
      }
  }}
  ```
- `handleSaveThreshold` implementation:
  ```typescript
  const handleSaveThreshold = async (value: number) => {
      setIsSaving(true);
      try {
          const response = await setInferenceThreshold(
              props.currentAnnotationClass?.id,
              value
          );
          // Refresh slider icon value and training status button states from response
          setInferenceThreshold(response.data.inference_threshold);
          // Callback to refresh training status button states
          props.onStatusRefresh?.(response.data);
      } finally {
          setIsSaving(false);
      }
  };
  ```

### UI placement

- In the `ClassesPane` render, next to the `TrainingStatusButton` (around line 104-108), add a threshold icon + value:
  ```tsx
  <div 
    ref={sliderRef}
    onMouseEnter={() => {
        setShowSlider(true);
        setSliderValue(inferenceThreshold ?? 0.5);
    }}
    onMouseLeave={() => {
        setShowSlider(false);
        if (inferenceThreshold !== null && Math.abs(sliderValue - inferenceThreshold) > 0.001) {
            handleSaveThreshold(sliderValue);
        }
    }}
    style={{ position: 'relative', display: 'inline-block' }}
  >
      <Button 
          variant="outline-secondary" 
          size="sm" 
          className="ms-1"
          disabled={inferenceThreshold === null}
      >
          {isSaving ? (
              <Spinner animation="border" style={{ width: '1rem', height: '1rem' }} />
          ) : (
              <>
                  <Target /> {inferenceThreshold?.toFixed(2) ?? '—'}
              </>
          )}
      </Button>
      {showSlider && inferenceThreshold !== null && (
          <div style={{ position: 'absolute', top: '100%', left: 0, zIndex: 20, backgroundColor: 'white', padding: 8, borderRadius: 4, boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
              <input 
                  type="range" 
                  min="0.01" 
                  max="0.99" 
                  step="0.01" 
                  value={sliderValue}
                  onChange={(e) => setSliderValue(parseFloat(e.target.value))}
              />
              <span>{sliderValue.toFixed(2)}</span>
          </div>
      )}
  </div>
  ```

### Props update

- Add to `ClassesPane` interface:
  ```typescript
  inferenceThreshold: number | null;
  setInferenceThreshold: (threshold: number) => void;
  onStatusRefresh?: (status: DLActorStatus) => void;
  ```
- `onStatusRefresh` allows the parent (`annotationPage.tsx`) to update the training status button states after a threshold change.
- Pass from `annotationPage.tsx` (lift `inferenceThreshold` state up or keep local to `ClassesPane`)

---

## 6. Frontend: Wire threshold into annotationPage.tsx

**File:** `quickannotator/client/src/routes/annotationPage.tsx`

- Add state for `inferenceThreshold` (extracted from actor status):
  ```typescript
  const [inferenceThreshold, setInferenceThreshold] = useState<number | null>(null);
  ```

- Extract `inference_threshold` from the `DLActorStatus` response when fetching actor status:
  ```typescript
  setInferenceThreshold(status.inference_threshold);
  ```

- Pass props to `ClassesPane`:
  ```tsx
  <ClassesPane
      inferenceThreshold={inferenceThreshold}
      setInferenceThreshold={setInferenceThreshold}
      onStatusRefresh={(status) => {
          // Update training status button states
          // Update inference threshold from response
          setInferenceThreshold(status.inference_threshold);
      }}
      // ... other props
  />
  ```

---

## File change summary

| File | Change |
|------|--------|
| `quickannotator/constants.py` | No change (keep as fallback default) |
| `quickannotator/dl/ray_jackson.py` | Add `inference_threshold` attr, getter, setter, include in `get_detailed_state` |
| `quickannotator/dl/training.py` | Read threshold from actor, pass to `run_inference()` |
| `quickannotator/dl/inference.py` | Add `inference_threshold` param to `run_inference()` and `postprocess_output()`, use it instead of `constants.INFERENCE_THRESHOLD` |
| `quickannotator/api/v1/ray/models.py` | Add `SetInferenceThresholdArgsSchema`, extend `GetDLActorStatusResponseSchema` with `inference_threshold` field |
| `quickannotator/api/v1/ray/routes.py` | Add `SetInferenceThresholdResource` endpoint |
| `quickannotator/db/crud/tile.py` | No change (uses existing `reset_all_PROCESSING_tiles`) |
| `quickannotator/client/src/types.ts` | Add `inference_threshold` to `DLActorStatus` interface |
| `quickannotator/client/src/helpers/api.ts` | Add `setInferenceThreshold` API helper |
| `quickannotator/client/src/components/classesPane.tsx` | Add threshold icon, slider, hover show/hide, spinner on save, `onStatusRefresh` callback, slider inactive until threshold present |
| `quickannotator/client/src/routes/annotationPage.tsx` | Extract `inference_threshold` from status, pass to `ClassesPane`, wire `onStatusRefresh` |
