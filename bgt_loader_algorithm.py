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

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsProcessingException,
)

from qgis.PyQt.QtCore import QCoreApplication
import requests
import time
import os
import zipfile
import tempfile
from datetime import datetime


class BgtLoaderAlgorithm(QgsProcessingAlgorithm):

    layers = [
        'bak',
        'begroeidterreindeel',
        'bord',
        'buurt',
        'functioneelgebied',
        'gebouwinstallatie',
        'installatie',
        'kast',
        'kunstwerkdeel',
        'mast',
        'onbegroeidterreindeel',
        'ondersteunendwaterdeel',
        'ondersteunendwegdeel',
        'ongeclassificeerdobject',
        'openbareruimte',
        'openbareruimtelabel',
        'overbruggingsdeel',
        'overigbouwwerk',
        'overigescheiding',
        'paal',
        'pand',
        'plaatsbepalingspunt',
        'put',
        'scheiding',
        'sensor',
        'spoor',
        'stadsdeel',
        'straatmeubilair',
        'tunneldeel',
        'vegetatieobject',
        'waterdeel',
        'waterinrichtingselement',
        'waterschap',
        'wegdeel',
        'weginrichtingselement',
        'wijk',
    ]

    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    POLYGON = 'POLYGON'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFolderDestination(self.OUTPUT_FOLDER, "Output folder")
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(self.POLYGON, "Selecteer een enkele feature uit de volgende laag:")
        )

        self.addParameter(QgsProcessingParameterNumber(
            'bbox_growth',
            'Buffer width',
            defaultValue=200.0
        ))

        # Dynamically add parameters for each layer
        for layer in self.layers:
            self.addParameter(
                QgsProcessingParameterBoolean(
                    f"{layer}",
                    f"Include {layer.replace('_', ' ').capitalize()}",
                    defaultValue=False
                )
            )

    def processAlgorithm(self, parameters, context, feedback):
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)

        # Get the feature source (the polygon layer)
        polygon_source = self.parameterAsSource(parameters, self.POLYGON, context)

        if not polygon_source:
            raise QgsProcessingException("Invalid polygon layer.")

        # Extract the WKT from the selected features
        features = polygon_source.getFeatures()
        wkt_polygon = ""

        for feature in features:
            if feature.isValid():
                geom = feature.geometry()
                wkt_polygon = geom.asWkt()  # Convert to WKT
                break

        if not wkt_polygon:
            raise QgsProcessingException("No valid polygon geometry found.")

        # Verzamel de geselecteerde lagen op basis van de checkboxen
        selected_layers = []
        for layer in self.layers:
            if self.parameterAsBoolean(parameters, layer, context):
                selected_layers.append(layer)

        feedback.pushInfo(f"Geselecteerde lagen: {', '.join(selected_layers)}")

        # Hier wordt feedback toegevoegd aan de download_geodata methode
        self.download_geodata(wkt_polygon, output_folder, selected_layers, feedback, parameters, context)

        return {}

    def download_geodata(self, wkt_polygon, output_folder, selected_layers, feedback, parameters, context):
        base_url = "https://api.pdok.nl/lv/bgt/download/v1_0/full/custom"
        headers = {'Content-Type': 'application/json'}

        payload = {
            "format": "gmllight",
            "geofilter": wkt_polygon,
            "featuretypes": selected_layers
        }

        feedback.pushInfo(f"Payload: {payload}")

        try:
            response = requests.post(base_url, headers=headers, json=payload)
            if response.status_code == 202:
                download_request_id = response.json().get("downloadRequestId")
                if not self.check_status(download_request_id, base_url, feedback):
                    self.download_data(download_request_id, base_url, output_folder, wkt_polygon, feedback, parameters, context)
            else:
                feedback.pushInfo(f"Error retrieving data: {response.status_code}\n{response.text}")

        except requests.RequestException as e:
            feedback.pushInfo(f"An error occurred while retrieving data: {str(e)}")

    def check_status(self, download_request_id, base_url, feedback):
        status_url = f"{base_url}/{download_request_id}/status"
        headers = {'Content-Type': 'application/json'}

        while True:
            response = requests.get(status_url, headers=headers)
            if response.status_code == 201:
                return False
            elif response.status_code == 200:
                time.sleep(5)
            else:
                feedback.pushInfo(f"Error checking status: {response.status_code}\n{response.text}")
                return True

    def download_data(self, download_request_id, base_url, output_folder, wkt_polygon, feedback, parameters, context):
        status_url = f"{base_url}/{download_request_id}/status"
        headers = {'Content-Type': 'application/json'}

        response = requests.get(status_url, headers=headers)
        if response.status_code == 201:
            download_href = response.json()["_links"]["download"]["href"]
            full_download_url = f"https://api.pdok.nl{download_href}"

            data_response = requests.get(full_download_url)
            if data_response.status_code == 200:
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                output_path = os.path.join(output_folder, f"geodata_{download_request_id}.zip")
                with open(output_path, 'wb') as f:
                    f.write(data_response.content)
                feedback.pushInfo(f"Data saved to {output_path}")
                bbox_growth = self.parameterAsDouble(parameters, 'bbox_growth', context)
                self.extract_and_load_data(output_path, output_folder, wkt_polygon, feedback, bbox_growth, parameters, context)
            else:
                feedback.pushInfo("Error downloading data.")
        else:
            feedback.pushInfo("Error obtaining download URL.")

    def extract_and_load_data(self, zip_path, output_folder, wkt_polygon, feedback, bbox_growth, parameters, context):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_folder)
            extracted_files = zip_ref.namelist()

        for file_name in extracted_files:
            file_path = os.path.join(output_folder, file_name)

            if not file_name.lower().endswith(".gml"):
                feedback.pushInfo(f"Unsupported file type for automatic loading: {file_name}")
                continue

            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if not layer.isValid():
                feedback.pushInfo(f"Could not load layer: {file_path}")
                continue

            layer.setSubsetString('"eindRegist" IS NULL')

            bbox_growth = self.parameterAsDouble(parameters, 'bbox_growth', context)
            clipped_layer = self.clip_layer_to_polygon(layer, wkt_polygon, file_name, feedback, bbox_growth)
            QgsProject.instance().addMapLayer(clipped_layer)

            feedback.pushInfo(f"Layer loaded and corrected in QGIS: {file_path}")

    def clip_layer_to_polygon(self, layer, polygon_wkt, original_name, feedback, bbox_growth):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(original_name)[0]
        clipped_layer_path = os.path.join(tempfile.gettempdir(), f"clipped_{base_name}_{timestamp}.shp")

        clipping_geometry = QgsGeometry.fromWkt(polygon_wkt).boundingBox()
        clipping_geometry.grow(bbox_growth)
        clipping_geometry = QgsGeometry.fromRect(clipping_geometry)

        geometry_type = layer.geometryType()
        feedback.pushInfo(f"Layer geometryType: {geometry_type.name}")  
        if geometry_type == QgsWkbTypes.LineGeometry:
            clipped_layer = QgsVectorLayer(f"LineString?crs={layer.crs().authid()}", "Temporary Layer", "memory")
        else:
            clipped_layer = QgsVectorLayer(f"{geometry_type.name}?crs={layer.crs().authid()}", "Temporary Layer", "memory")
        clipped_provider = clipped_layer.dataProvider()
        clipped_provider.addAttributes(layer.fields())
        clipped_layer.updateFields()

        features = layer.getFeatures()
        for feature in features:
            geom = feature.geometry()
            if geom.intersects(clipping_geometry):
                clipped_feature = QgsFeature()
                clipped_feature.setGeometry(geom.intersection(clipping_geometry))
                clipped_feature.setAttributes(feature.attributes())
                clipped_provider.addFeature(clipped_feature)

        QgsVectorFileWriter.writeAsVectorFormat(clipped_layer, clipped_layer_path, "utf-8", layer.crs(), "ESRI Shapefile")
        clipped_layer = QgsVectorLayer(clipped_layer_path, f"{base_name}_{timestamp}", "ogr")
        
        if not clipped_layer.isValid():
            raise QgsProcessingException(f"Error loading clipped layer: {clipped_layer_path}")

        return clipped_layer

    
    def name(self):
        return 'bgtloader'

    def displayName(self):
        return self.tr('Download and import BGT layers')

    def group(self):
       # return self.tr(self.groupId())
        pass

    def groupId(self):
        # return 'BGT Loader'
        pass

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return BgtLoaderAlgorithm()
