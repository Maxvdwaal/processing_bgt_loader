# BgtLoader

**BgtLoader** is a QGIS processing tool designed to help users download Dutch BGT (Basisregistratie Grootschalige Topografie) data for a specific polygon area selected by the user. This tool fetches and processes the data, making it available for further analysis and visualization in QGIS.

## Features

- **Download BGT data**: Select polygonal areas and download associated BGT layers.
- **Supported layers**: The tool supports downloading data for multiple BGT layers such as `bak`, `buurt`, `pand`, `wegdeel`, and many others (full list below).
- **Buffer customization**: Users can specify a buffer distance to expand the selected polygon area.
- **Automated data handling**: After downloading, the data is clipped to the polygon area and buffered, and then saved as shapefiles for immediate use in QGIS.

## Supported BGT Layers

The following layers can be downloaded and processed by the tool:
- `bak`, `begroeidterreindeel`, `bord`, `buurt`, `functioneelgebied`, `gebouwinstallatie`, `installatie`, `kast`, `kunstwerkdeel`, `mast`, `onbegroeidterreindeel`, `ondersteunendwaterdeel`, `ondersteunendwegdeel`, `ongeclassificeerdobject`, `openbareruimte`, `openbareruimtelabel`, `overbruggingsdeel`, `overigbouwwerk`, `overigescheiding`, `paal`, `pand`, `plaatsbepalingspunt`, `put`, `scheiding`, `sensor`, `spoor`, `stadsdeel`, `straatmeubilair`, `tunneldeel`, `vegetatieobject`, `waterdeel`, `waterinrichtingselement`, `waterschap`, `wegdeel`, `weginrichtingselement`, `wijk`

## Installation

1. Ensure you have QGIS installed on your system. You can download it from [QGIS official site](https://qgis.org/).
2. Download or clone the **BgtLoader** plugin repository:
    ```bash
    git clone https://github.com/username/BgtLoader.git
    ```
3. Open QGIS and navigate to `Plugins > Manage and Install Plugins...`.
4. Click on `Install from ZIP` and select the `BgtLoader` plugin ZIP file from your system.
5. Once installed, access the plugin from the QGIS Processing Toolbox.

## Usage

1. In QGIS, open the Processing Toolbox.
2. Search for `Download and import BGT layers` in the toolbox or find it under the `BgtLoader` section.
3. Follow the steps below to use the tool:
    - **Select a polygon**: Choose a polygon layer from your project to define the area of interest.
    - **Buffer Distance**: Optionally, define a buffer distance (in meters) to expand the selected polygon.
    - **Choose BGT Layers**: Select one or more BGT layers to download.
4. Run the tool. The BGT data will be downloaded, processed, and clipped to your selected area. The output shapefiles will be automatically added to your QGIS project.

## Example

Here's an example of using **BgtLoader**:
1. Select a polygon feature representing a neighborhood in Amsterdam.
2. Set a buffer distance of 200 meters.
3. Select `pand`, `wegdeel`, and `waterdeel` layers.
4. Run the tool, and the downloaded BGT data will be clipped to the neighborhood's boundaries with a 200m buffer.

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bug fix:
    ```bash
    git checkout -b feature/my-feature
    ```
3. Commit your changes:
    ```bash
    git commit -am 'Add new feature'
    ```
4. Push to your branch:
    ```bash
    git push origin feature/my-feature
    ```
5. Create a pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contact

For questions or feedback, please reach out to the project maintainer:
- **Max van der Waal** – m.vanderwaal@tudelft.nl
