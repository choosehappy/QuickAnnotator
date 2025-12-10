# Welcome to QuickAnnotator's Documentation!
QuickAnnotator is an open-source web application designed for efficient digital pathology image annotation. This documentation provides comprehensive guides on installation, usage, and development of QuickAnnotator. 

Where applicable, video tutorials from our [YouTube playlist](https://www.youtube.com/playlist?list=PLOk1nLH1Kl25qhN7j8_cdhVyqCN9P3OGy) are embedded for further clarity.

## Key Features
- **User-Friendly Interface**: Intuitive design for easy navigation and annotation of large images.
- **Multi-Format Support**: Compatible with various image formats commonly used in pathology.
- **Active Deep Learning**: QA features a deep learning model which predicts annotations as you annotate. The model improves over time as more annotations are added.
- **Dockerized Deployment**: Easy to set up and deploy using Docker containers.
- **Compatible with the Digital Slide Archive (DSA)**: Annotations in QuickAnnotator can be easily exported to a DSA instance.


## Contributing
Contributions are welcome! Feel free to fork the repository, make improvements, and submit pull requests.

## License
QuickAnnotator is provided under the [MIT License](https://opensource.org/licenses/MIT).

## Links
- Github: [https://github.com/choosehappy/QuickAnnotator](https://github.com/choosehappy/QuickAnnotator)
- Docker Hub: [https://hub.docker.com/r/histotools/quickannotator](https://hub.docker.com/r/histotools/quickannotator)

## Citation
Read the related paper in Journal of Pathology - Clinical Research: [Quick Annotator: an open-source digital pathology based rapid image annotation tool](https://onlinelibrary.wiley.com/doi/full/10.1002/cjp2.229)

Please use below to cite this paper if you find this repository useful or if you use the software shared here in your research.
```
  @misc{miao2021quick,
      title={Quick Annotator: an open-source digital pathology based rapid image annotation tool}, 
      author={Runtian Miao and Robert Toth and Yu Zhou and Anant Madabhushi and Andrew Janowczyk},
      year={2021},
      journal = {The Journal of Pathology: Clinical Research},
      issn = {2056-4538}
  }
```

---

```{toctree}
:maxdepth: 2
:caption: Contents:

installation
usage
unit_testing
developer_guide
```
