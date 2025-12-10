# User Guide
We provide a step-by-step user manual here.

## 1. Running QuickAnnotator
After installation, open a terminal session within the QuickAnnotator docker container and run the following command to start QuickAnnotator:
```bash
quickannotator
```

In a second terminal session, run the quickannotator user interface:
```bash
npm run dev
```

You can then access QuickAnnotator by navigating to `http://localhost:5173` in your web browser.

## 2. Creating a project
Projects in QuickAnnotator help organize your images and annotations into independent workspaces.
<iframe width="100%" height="560" src="https://www.youtube.com/embed/7tDFsaEMzm0?si=6S0C8FjqsMKGylfU" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## 3. Uploading images
QuickAnnotator supports images in OpenSlide compatible formats. You can upload images directly from your local machine or mount an NAS share containing your images.

### 3.1. Manual Upload
<iframe width="100%" height="560" src="https://www.youtube.com/embed/t2nWiaZHKjA?si=jUGXR9A_tPWPwPjL" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### 3.2. TSV Upload
You can alternatively upload images using a TSV file. This is particularly useful when you have a large number of images to upload, or if you also wish to upload existing annotations alongside the images. The TSV file should have the following format, where each row corresponds to an image and its associated annotation files (if any):

| filepath            | CLASS_NAME_annotations        | ANOTHER_CLASS_annotations             |
| ------------------- | ----------------------------- | ------------------------------------- |
| /path/to/image1.svs | /path/to/annotations1.geojson | /path/to/another_annotations1.geojson |
| /path/to/image2.svs | /path/to/annotations2.geojson | /path/to/another_annotations2.geojson |

```{important}
QuickAnnotator will only process annotation columns that match the format `CLASS_NAME_annotations`, where `CLASS_NAME` is an existing class within the current project. See [Adding Annotation Classes](#adding-annotation-classes) for more information.
```

<iframe width="100%" height="560" src="https://www.youtube.com/embed/2zf_cC5FFV8?si=9JRhAfM2ez14LF9s" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### 3.3. DSA Upload (Planned)
```{note}
A future version of QuickAnnotator will support direct upload of images from a Digital Slide Archive (DSA) instance.
```

## 4. Uploading existing annotations
Some users have existing annotations in geojson format that they wish to upload into QuickAnnotator to help the DL model learn faster. A typical geojson file may look like the following, where each polygon is stored as a "Feature" within a "FeatureCollection":
```json
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [54993, 7573],
                        [54865, 7577],
                        [54993, 7573]
                    ]
                ]
            }
        }
    ]
}
```

```{note}
Geojson features also support properties, however QuickAnnotator currently ignores these properties during upload.
```


### 4.1. Manual Upload

### 4.2. TSV Upload

## 5. Annotating images

<iframe width="100%" height="560" src="https://www.youtube.com/embed/wtL5vK_tj4c?si=xqfAk2AV0UaL_W33" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## 6. Using Deep Learning Assistance
QuickAnnotator's deep learning model will automatically start learning from your manual annotations and provide annotation suggestions as you work. To accept a suggested annotation, use the "Import Predictions" button from the toolbar. You can control whether to click or lasso select suggested annotations using the CTRL key.

```{note}
Video tutorial coming soon!
```

## 7. Adding annotation classes
<iframe width="100%" height="560" src="https://www.youtube.com/embed/9N1PoJS4lkg?si=KNuph7N-zQYdn8o8" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## 8. Exporting annotations
QuickAnnotator provides multiple options for exporting annotations.

### 8.1. Save Locally
<iframe width="100%" height="560" src="https://www.youtube.com/embed/20r5xQaZ-6k?si=H2LWvHclC-RGTMvx" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### 8.2. Push to Digital Slide Archive (DSA)

```{note}
Video tutorial coming soon!
```