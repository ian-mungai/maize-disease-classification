# Maize Disease Classification

A historical bachelor's capstone: a Laravel application sends maize leaf images to a Flask service backed by a TensorFlow convolutional neural network (CNN).

## Background

This repository was pulled from the original private project and cleaned up for public release: account records, the database dump, local files and the original Git history were left out. Documentation was added. The code, the notebook with its saved outputs and the model files are unchanged; nothing was retrained or added. The original project was completed in 2022; its notebook was added later, so the notebook's results do not establish where the bundled model came from.

## Install

The historical Python environment is recorded in [`flask-app/requirements.txt`](flask-app/requirements.txt). It includes TensorFlow 2.4.0, tensorflow-cpu 2.4.3, Keras 2.4.3 and Flask 1.1.2. Compatibility with current macOS or Python has not been established. The Laravel application declares PHP `^7.3|^8.0` and Laravel `^8.54` in [`web-app/composer.json`](web-app/composer.json); its Composer and npm lockfiles are preserved. Runtime configuration is listed in [`web-app/.env.example`](web-app/.env.example), which contains placeholders, not credentials.

Do not expose the historical application to a network. See [Limitations](#limitations) before attempting any local runtime setup.

## Usage

The application has not been run since it was cleaned up for release. Setup and run steps will be added here once a local run has been verified.

The notebook can be opened in Jupyter to read its code and saved outputs without running it.

## Architecture

![Historical flow: leaf images feed a training notebook; Laravel sends a stored image path to Flask, which reads a TensorFlow model and returns a class; MySQL holds users, predictions and recommendations](docs/architecture/architecture.png)

The editable source is [`docs/architecture/architecture.html`](docs/architecture/architecture.html). The diagram describes the checked-in implementation, not a running deployment. Model export is shown separately because the notebook and bundled checkpoint have no verified run-level link.

To render the self-contained diagram with an installed Chrome browser, run from the repository root:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1200,1600 --virtual-time-budget=5000 --screenshot=docs/architecture/architecture.png "file://$PWD/docs/architecture/architecture.html"
```

## Data

The notebook works with maize leaf images in four classes: Blight, Common Rust, Gray Leaf Spot and Healthy. Its saved output reports 3,560 files in the training folder and 628 in a separate test folder. The image dataset is not included and no dataset download is provided here.

The images come from the [Corn or Maize Leaf Disease Dataset](https://www.kaggle.com/datasets/smaranjitghose/corn-or-maize-leaf-disease-dataset) on Kaggle, compiled by Smaranjit Ghose. The original download, dated Jul 8 2021, matches that listing: 4,188 images, the same uncompressed size and the same count in each class. Its train and test folders hold the notebook's 3,560 and 628 images.

The retained notebook image shows only leaf samples and class labels. Account records, user uploads and database dumps are excluded.

### Data Sources and Credits

The Kaggle listing states "Data files © Original Authors". Its compiler built the set from the PlantVillage and PlantDoc datasets, notes that the original authors keep their rights and asks users to credit them:

- **PlantDoc:** Singh D, Jain N, Jain P, Kayal P, Kumawat S and Batra N. "PlantDoc: A Dataset for Visual Plant Disease Detection." Proceedings of the 7th ACM IKDD CoDS and 25th COMAD, 2020, pp. 249–253. Images are licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) ([dataset repository](https://github.com/pratikkayal/PlantDoc-Dataset)).
- **PlantVillage (version cited by the Kaggle listing):** Arun Pandian J and Geetharamani Gopal. "Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep Convolutional Neural Network." Mendeley Data, V1, 2019, [doi:10.17632/tywbtsjrjv.1](https://doi.org/10.17632/tywbtsjrjv.1). Released under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- **Compilation:** Smaranjit Ghose, [Corn or Maize Leaf Disease Dataset](https://www.kaggle.com/datasets/smaranjitghose/corn-or-maize-leaf-disease-dataset), Kaggle, updated Nov 11 2020.

**Changes:** the notebook's embedded image shows sample leaves from these sources, resized and arranged in a grid with class labels. Which source each sample came from is not recorded, so both are credited. The MIT License covers only the original project code, not these images.

## Deploy and Teardown

There is no deployment workflow, live demo or newly provisioned infrastructure. The historical application has not been started since the cleanup.

## Repository Layout

| Path | Contents |
| --- | --- |
| `Maize_Diseases_Detection_Model.ipynb` | Original training code and saved outputs |
| `flask-app/` | Historical prediction endpoint and four TensorFlow model files |
| `web-app/` | Laravel interface, migrations, policies, views and dependency lockfiles |
| `docs/architecture/` | Architecture diagram and its editable HTML source |

## Limitations

The notebook records test accuracy `0.8105095624923706` and test loss `2.938377618789673`. These are saved outputs, not a new measurement. Training and validation use seeds 344 and 564 on the same folder; overlap compromises validation and the selection of the best checkpoint. No retraining or corrected validation result is claimed.

The Flask service accepts a server image path, reloads the model for each request and starts with debug enabled on all interfaces. The Laravel interface saves images in a public directory, stores prediction results and looks up editable disease-to-pesticide recommendations. These behaviors are kept as they were in the original project. Recommendation correctness, farm use, security, production readiness and current runtime compatibility have not been validated.

## Contributing

Individual project; contributions are not accepted.

## License

The original project code is licensed under the [MIT License](LICENSE), Existing third-party notices and license metadata remain intact. This license choice does not cover the dataset or the embedded leaf image; their sources and terms are in [Data Sources and Credits](#data-sources-and-credits).
