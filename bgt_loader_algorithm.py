# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BgtLoader
                                 A QGIS processing tool
 This tool helps downloading the Dutch BGT-data within a selected polygon area.
                              -------------------
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-10-08
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Max van der Waal
        email                : m.vanderwaal@tudelft.nl
 ***************************************************************************/
"""

# Import necessary QGIS libraries
from qgis.core import ( # type: ignore
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsCoordinateReferenceSystem,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsProcessingException,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsProcessing
)

from qgis.PyQt.QtCore import QCoreApplication # type: ignore

# Import necessary standard libraries
import requests
import time
import os
import zipfile
import tempfile
from datetime import datetime


class BgtLoaderAlgorithm(QgsProcessingAlgorithm):
    """
    QGIS processing tool for downloading Dutch BGT-data within a selected polygon.
    """

    # Define the available layers for download from BGT
    layers = [
        'bak', 'begroeidterreindeel', 'bord', 'buurt', 'functioneelgebied',
        'gebouwinstallatie', 'installatie', 'kast', 'kunstwerkdeel', 'mast',
        'onbegroeidterreindeel', 'ondersteunendwaterdeel', 'ondersteunendwegdeel',
        'ongeclassificeerdobject', 'openbareruimte', 'openbareruimtelabel',
        'overbruggingsdeel', 'overigbouwwerk', 'overigescheiding', 'paal', 'pand',
        'plaatsbepalingspunt', 'put', 'scheiding', 'sensor', 'spoor', 'stadsdeel',
        'straatmeubilair', 'tunneldeel', 'vegetatieobject', 'waterdeel',
        'waterinrichtingselement', 'waterschap', 'wegdeel', 'weginrichtingselement', 'wijk'
    ]

    # Define constants
    temp_dir = 'temp_dir'  # Directory for temporary files
    POLYGON = 'POLYGON'  # Parameter for input polygon

    def initAlgorithm(self, config):
        """
        Initialize algorithm with input parameters.
        """
        # Input: User-selected polygon feature source
        self.addParameter(QgsProcessingParameterFeatureSource(self.POLYGON, "Selecteer een enkele feature uit de volgende laag:"))

        # Input: Buffer distance for polygon
        self.addParameter(QgsProcessingParameterNumber('buffer_distance', 'Bufferbreedte in meters:', defaultValue=200.0))

        # Output: Define feature sinks for each selected BGT layer
        for layer in self.layers:
            self.addParameter(QgsProcessingParameterFeatureSink(layer, f"{layer}", QgsProcessing.TypeVectorAnyGeometry, createByDefault=False, optional=True))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Main process for running the algorithm.
        - Extract polygon geometry.
        - Download and process BGT layers.
        """
        # Create persistent temporary directory to avoid deletion errors
        temp_dir = tempfile.mkdtemp()  
        feedback.pushInfo(f"Using persistent temporary directory: {temp_dir}")

        try:
            # Get input polygon feature source
            polygon_source = self.parameterAsSource(parameters, self.POLYGON, context)
            if not polygon_source:
                raise QgsProcessingException("Invalid polygon layer.")

            # Extract the geometry of the first valid polygon feature
            features = polygon_source.getFeatures()
            wkt_polygon = ""

            target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            source_crs = polygon_source.sourceCrs()
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

            for feature in features:
                if feature.isValid():
                    geom = feature.geometry()
                    geom.transform(transform)
                    wkt_polygon = geom.asWkt()
                    break

            if not wkt_polygon:
                raise QgsProcessingException("No valid polygon geometry found.")

            # Get the list of selected layers
            selected_layers = [layer for layer in self.layers if parameters.get(layer) is not None]
            feedback.pushInfo(f"Geselecteerde lagen: {', '.join(selected_layers)}")

            # Download and process BGT data
            result = self.download_geodata(wkt_polygon, temp_dir, selected_layers, feedback, parameters, context)

            # Return processed layer paths
            outputs = {layer_name: sink_path for layer_name, sink_path in result.items()}
            return outputs
        except Exception as e:
            # Catch any exceptions and provide feedback
            feedback.reportError(f"Error during processing: {str(e)}")
            raise QgsProcessingException(f"Processing error: {str(e)}")

    def download_geodata(self, wkt_polygon, temp_dir, selected_layers, feedback, parameters, context):
        """
        Download geodata from PDOK API based on the WKT polygon and selected layers.
        """
        base_url = "https://api.pdok.nl/lv/bgt/download/v1_0/full/custom"
        headers = {'Content-Type': 'application/json'}

        # Define API request payload
        payload = {"format": "gmllight", "geofilter": wkt_polygon, "featuretypes": selected_layers}
        feedback.pushInfo(f"Payload: {payload}")

        result_paths = {}

        try:
            # Send request to PDOK API
            response = requests.post(base_url, headers=headers, json=payload)
            if response.status_code == 202:
                download_request_id = response.json().get("downloadRequestId")
                
                # Check the status of the download request
                if not self.check_status(download_request_id, base_url, feedback):
                    # Proceed with downloading the data if available
                    result_paths = self.download_data(download_request_id, base_url, temp_dir, wkt_polygon, feedback, parameters, context)
            else:
                feedback.pushInfo(f"Error retrieving data: {response.status_code}\n{response.text}")
        except requests.RequestException as e:
            feedback.pushInfo(f"An error occurred while retrieving data: {str(e)}")

        return result_paths

    def check_status(self, download_request_id, base_url, feedback):
        """
        Check the status of the download request until it's ready.
        """
        status_url = f"{base_url}/{download_request_id}/status"
        headers = {'Content-Type': 'application/json'}

        while True:
            # Check the status of the request
            response = requests.get(status_url, headers=headers)
            if response.status_code == 201:
                return False  # Data is ready
            elif response.status_code == 200:
                time.sleep(5)  # Wait for the process to complete
            else:
                feedback.pushInfo(f"Error checking status: {response.status_code}\n{response.text}")
                return True

    def download_data(self, download_request_id, base_url, temp_dir, wkt_polygon, feedback, parameters, context):
        """
        Download the requested BGT data after successful status check.
        """
        status_url = f"{base_url}/{download_request_id}/status"
        headers = {'Content-Type': 'application/json'}

        # Get download link from the status response
        response = requests.get(status_url, headers=headers)
        if response.status_code == 201:
            download_href = response.json()["_links"]["download"]["href"]
            full_download_url = f"https://api.pdok.nl{download_href}"

            # Download the actual data file (zip)
            data_response = requests.get(full_download_url)
            if data_response.status_code == 200:
                output_path = os.path.join(temp_dir, f"geodata_{download_request_id}.zip")
                with open(output_path, 'wb') as f:
                    f.write(data_response.content)
                feedback.pushInfo(f"Data saved to {output_path}")

                # Extract and load the downloaded data
                buffer_distance = self.parameterAsDouble(parameters, 'buffer_distance', context)
                result_paths = self.extract_and_load_data(output_path, temp_dir, wkt_polygon, feedback, buffer_distance, parameters, context)
                return result_paths
            else:
                feedback.pushInfo("Error downloading data.")
        else:
            feedback.pushInfo("Error obtaining download URL.")

        return {}

    def extract_and_load_data(self, zip_path, temp_dir, wkt_polygon, feedback, buffer_distance, parameters, context):
        """
        Extract the zip file and process the GML files.
        """
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)  # Extract all files to temp directory
            extracted_files = zip_ref.namelist()  # List of extracted file names

        result_paths = {}

        # Process each extracted file
        for file_name in extracted_files:
            file_path = os.path.join(temp_dir, file_name)

            # Only process GML files that start with 'bgt_'
            if not file_name.lower().endswith(".gml") or not file_name.startswith("bgt_"):
                feedback.pushInfo(f"Skipping unsupported or unrecognized file: {file_name}")
                continue

            layer_name = file_name.split("bgt_")[-1].split(".gml")[0]

            # Skip unrecognized layers
            if layer_name not in self.layers:
                feedback.pushInfo(f"Layer {layer_name} not recognized in selected layers.")
                continue

            # Load the layer using QGIS
            layer = QgsVectorLayer(file_path, layer_name, "ogr")
            if not layer.isValid():
                feedback.pushInfo(f"Failed to load layer: {file_name}")
                continue

            # Set CRS to EPSG:28992 (Dutch RD New coordinate system)
            layer.setCrs(QgsCoordinateReferenceSystem("EPSG:28992"))

            # Clip the layer to the input polygon and process it
            clipped_layer = self.clip_layer_to_polygon(layer, wkt_polygon, file_name, feedback, buffer_distance)

            # Prepare to save the clipped layer to the defined sinks
            sink, sink_path = self.parameterAsSink(parameters, layer_name, context, clipped_layer.fields(), clipped_layer.wkbType(), clipped_layer.sourceCrs())

            # Add each feature to the sink
            for feature in clipped_layer.getFeatures():
                sink.addFeature(feature, QgsFeatureSink.FastInsert)

            feedback.pushInfo(f"Layer {layer_name} processed and saved.")
            result_paths[layer_name] = sink_path  # Save output path for the layer

        return result_paths

    def clip_layer_to_polygon(self, layer, polygon_wkt, original_name, feedback, buffer_distance):
        """
        Clip the input layer to the provided polygon and buffer it.
        """
        # Create a timestamped output file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(original_name)[0]
        clipped_layer_path = os.path.join(tempfile.gettempdir(), f"clipped_{base_name}_{timestamp}.shp")

        # Create a buffered geometry from the input polygon WKT
        polygon_geometry = QgsGeometry.fromWkt(polygon_wkt)
        buffered_geometry = polygon_geometry.buffer(buffer_distance, 1)

        # Determine the layer's geometry type
        geometry_type = layer.geometryType()
        feedback.pushInfo(f"Layer geometryType: {geometry_type.name}")
        
        # Create an in-memory layer for the clipped data based on geometry type
        if geometry_type == QgsWkbTypes.LineGeometry:
            clipped_layer = QgsVectorLayer(f"LineString?crs={layer.crs().authid()}", "Temporary Layer", "memory")
        else:
            clipped_layer = QgsVectorLayer(f"{geometry_type.name}?crs={layer.crs().authid()}", "Temporary Layer", "memory")

        # Add attributes and update fields
        clipped_provider = clipped_layer.dataProvider()
        clipped_provider.addAttributes(layer.fields())
        clipped_layer.updateFields()
        
        # Clip features to the buffered geometry
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom.intersects(buffered_geometry):
                clipped_feature = QgsFeature()
                clipped_feature.setGeometry(geom.intersection(buffered_geometry))
                clipped_feature.setAttributes(feature.attributes())
                clipped_provider.addFeature(clipped_feature)

        # Save the clipped layer as a shapefile
        QgsVectorFileWriter.writeAsVectorFormat(clipped_layer, clipped_layer_path, "utf-8", QgsCoordinateReferenceSystem("EPSG:28992"), "ESRI Shapefile")

        # Load the clipped layer back into QGIS for further use
        clipped_layer = QgsVectorLayer(clipped_layer_path, f"{base_name}_{timestamp}", "ogr")
        if not clipped_layer.isValid():
            raise QgsProcessingException(f"Error loading clipped layer: {clipped_layer_path}")

        return clipped_layer

    def name(self):
        return 'bgtloader'

    def displayName(self):
        return self.tr('Download and import BGT layers')

    def tr(self, string):
        """
        Translate string for QGIS localization.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """
        Create a new instance of the algorithm.
        """
        return BgtLoaderAlgorithm()
