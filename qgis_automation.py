import os
import sys
sys.path.append("C:/OSGeo4W/apps/qgis/python")

from qgis.core import QgsApplication

qgs = QgsApplication([], False)
qgs.initQgis()


# 1. 데이터 불러오기
print("1")
uri = f"file:///C:/Code/Interbird/input/OC_TEMP.csv?encoding=EUC-KR&type=csv&maxFields=10000&detectTypes=yes&xField=x&yField=y&crs=EPSG:4326&spatialIndex=no&subsetIndex=no&watchFile=no&field=daytime:datetime"
OC_TEMP_LAYER = QgsVectorLayer(uri, "OC_TEMP_LAYER", "delimitedtext")


# 2. 공간 인덱스 생성
print("2")
provider = OC_TEMP_LAYER.dataProvider()
if not provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
    pass
    #print("공간 인덱스를 생성할 수 없습니다.")
else:
    if provider.createSpatialIndex():
        pass
        #print("공간 인덱스가 성공적으로 생성되었습니다.")
    else:
        pass
        #print("공간 인덱스 생성 중 오류가 발생했습니다.")


# 3. 포인트 데이터에 날짜 필터 적용
print("3")
expression = '"daytime" = \'2023-05-01T10:00:00.000\''
OC_TEMP_LAYER.setSubsetString(expression)


# 4. 헥사곤 그리드 생성
print("4")

xmin = 655643.0368323465809226
xmax = 1414735.0931378039531410
ymin = 1450505.3176271202974021
ymax = 2118554.4563891696743667
params = {
    'TYPE': 4,  # Hexagon type
    #'EXTENT': f'{xmin},{xmax},{ymin},{ymax}',
    'EXTENT': f'{xmin},{xmax},{ymin},{ymax}',
    'HSPACING': 5000,
    'VSPACING': 5000,
    'HOVERLAY': 0,
    'VOVERLAY': 0,
    'CRS': 'EPSG:5179',
    'OUTPUT': 'memory:'
}
result = processing.run('qgis:creategrid', params)
HEX_GRID_LAYER = result['OUTPUT']
HEX_GRID_LAYER.setName("HEX_GRID_LAYER")
QgsProject.instance().addMapLayer(HEX_GRID_LAYER)


# 5. 헥사곤-포인트 속성 결합
print("5")
output_path = 'C:/Code/Interbird/output/HEX_TEMP_LAYER.shp'

# 저장된 레이어가 존재하는지 확인
if not os.path.exists(output_path):
    join_params = {
        'DISCARD_NONMATCHING': False,
        'INPUT': HEX_GRID_LAYER,
        'JOIN': OC_TEMP_LAYER,
        'JOIN_FIELDS': ['octemp'],
        'METHOD': 1,  # Mean
        'OUTPUT': output_path,
        'PREFIX': '',
        'SUMMARIES': [6]  # Mean
    }
    join_result = processing.run('qgis:joinbylocationsummary', join_params)

# 저장된 레이어를 다시 로드
HEX_TEMP_LAYER = QgsVectorLayer(output_path, "HEX_TEMP_LAYER", "ogr")
QgsProject.instance().addMapLayer(HEX_TEMP_LAYER)



# 6. 속성으로 추출 (Null 데이터 삭제)
print("6")
expr = '"octemp_mea" IS NOT NULL'
params = {
    'INPUT': HEX_TEMP_LAYER,
    'EXPRESSION': expr,
    'OUTPUT': 'memory:'
}
result = processing.run('qgis:extractbyexpression', params)
NN_TEMP_LAYER = result['OUTPUT']
NN_TEMP_LAYER.setName("NN_TEMP_LAYER")
QgsProject.instance().addMapLayer(NN_TEMP_LAYER)



# 7. 헥사곤에서 포인트 데이터 생성
print("7")
output_path = 'C:/Code/Interbird/output/CENT_TEMP_POINT.shp'

# 저장된 레이어가 존재하는지 확인
if not os.path.exists(output_path):
    params = {
        'ALL_PARTS': False,
        'INPUT': NN_TEMP_LAYER,
        'OUTPUT': output_path
    }
    result = processing.run('qgis:centroids', params)

# 저장된 레이어를 다시 로드
CENT_TEMP_POINT = QgsVectorLayer(output_path, "CENT_TEMP_POINT", "ogr")
QgsProject.instance().addMapLayer(CENT_TEMP_POINT)



# 8.크리깅 보간
print("8")
output_path = "C:/Code/Interbird/output/KRIG_TEMP_PREDICTION.sdat"

if not os.path.exists(output_path):
    print("DUDE IT TAKES TIME . . .")

    #입력 레이어의 경계를 구합니다.
    input_layer_path = "C:/Code/Interbird/output/CENT_TEMP_POINT.shp"  # 이 부분을 shp 파일 경로로 수정하세요.
    layer = QgsVectorLayer(input_layer_path, '', 'ogr')

    # 레이어 유효성 검사
    if not layer.isValid():
        print(f"레이어 {input_layer_path}는 유효하지 않습니다.")
    else:
        print(f"레이어 {input_layer_path}는 유효합니다.")

    coords = "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax)  # 이것은 좌표를 저장하는 문자열입니다.
    #ordinarykriging 함수의 입력 파라미터를 수정합니다.
    kriging_params = {
        'POINTS': input_layer_path,
        'FIELD': "octemp_mea",
        'TARGET_USER_XMIN': xmin,
        'TARGET_USER_XMAX': xmax,
        'TARGET_USER_YMIN': ymin,
        'TARGET_USER_YMAX': ymax,
        'TARGET_USER_SIZE': 1000.0,
        'TARGET_USER_FITS': 0,  # 0 for nodes, 1 for cells
        'PREDICTION': output_path,  # Update this with the actual path
        #'VARIANCE': "C:/Code/Interbird/KRIG_TEMP_VARIANCE.shp",  # Update this with the actual path
        'TQUALITY': 1,  # 0 for Standard Deviation, 1 for Variance
        'VAR_MAXDIST': 50000,
        'VAR_NCLASSES': 10,
        'VAR_NSKIP': 1,
        'VAR_MODEL': "a + b * x",
        'LOG': True,
        'BLOCK': True,
        'DBLOCK': 1000,
        'CV_METHOD': 3,  # 0 for none, 1 for leave one out, 2 for 2-fold, 3 for k-fold
        # 'CV_SUMMARY': 'path_to_save_cv_summary',  # Optional
        # 'CV_RESIDUALS': 'path_to_save_cv_residuals',  # Optional
        'CV_SAMPLES': 50,
        'SEARCH_RANGE': 0,  # 0 for local, 1 for global
        'SEARCH_RADIUS': 500000,
        'SEARCH_POINTS_ALL': 0,  # 0 for maximum number of nearest points, 1 for all points within search distance
        'SEARCH_POINTS_MIN': 4,
        'SEARCH_POINTS_MAX': 20
    }
    print("please")
    Output = processing.run('sagang:ordinarykriging', kriging_params)
    print("Run")

# 변환
KRIG_TEMP_PREDICTION_LAYER = QgsRasterLayer(output_path, 'KRIG_TEMP_PREDICTION')
#KRIG_TEMP_VARIANCE_LAYER = QgsRasterLayer("C:/Code/Interbird/KRIG_TEMP_VARIANCE.shp", 'KRIG_TEMP_VARIANCE')

# 이름 설정
KRIG_TEMP_PREDICTION_LAYER.setName('KRIG_TEMP_PREDICTION')
#KRIG_TEMP_VARIANCE_LAYER.setName('KRIG_TEMP_VARIANCE')

# 레이어 추가

QgsProject.instance().addMapLayer(KRIG_TEMP_PREDICTION_LAYER)
#QgsProject.instance().addMapLayer(KRIG_TEMP_VARIANCE_LAYER)






# 9. 보간 결과 마스킹
print("9. Masking Interpolated Data")

# 입력 파일 및 출력 파일 경로 설정
input_raster = output_path  # 보간된 래스터 파일 경로 (KRIG_TEMP_LAYER의 실제 경로)
masking_layer = "C:/Code/Interbird/input/Masking_data_30km.shp"  # 마스크 레이어
output_masked_raster = "C:/Code/Interbird/output/KRIG_TEMP_MASKED.tif"  # 마스킹된 래스터 결과물을 저장할 경로

# 이미 생성된 레이어가 있는지 확인
if not os.path.exists(output_masked_raster):
    # 마스크 도구 실행
    params = {
        'INPUT': input_raster,
        'MASK': masking_layer,
        'NODATA': -9999,
        'ALPHA_BAND': False,
        'CROP_TO_CUTLINE': True,
        'KEEP_RESOLUTION': True,
        'OPTIONS': "",
        'DATA_TYPE': 0,
        'OUTPUT': output_masked_raster
    }
    result = processing.run('gdal:cliprasterbymasklayer', params)

# 결과 레이어 추가
KRIG_TEMP_MASKED = QgsRasterLayer(output_masked_raster, "KRIG_TEMP_MASKED")
KRIG_TEMP_MASKED.setName('KRIG_TEMP_MASKED')
QgsProject.instance().addMapLayer(KRIG_TEMP_MASKED)



# 10.Kriging Raster to Point Data
print("10. Converting Raster Pixels to Points")

output_shp_path = 'C:/Code/Interbird/output/KRIG_TEMP_POINT.shp'

# 이미 파일이 존재하는지 확인
if not os.path.exists(output_shp_path):
    params = {
        'INPUT_RASTER': 'C:/Code/Interbird/output/KRIG_TEMP_MASKED.tif',
        'RASTER_BAND': 1,  # 첫 번째 밴드를 사용
        'FIELD_NAME': 'VALUE',
        'OUTPUT': output_shp_path
    }

    result = processing.run('native:pixelstopoints', params)
    KRIG_TEMP_POINT = QgsVectorLayer(result['OUTPUT'], "KRIG_TEMP_POINT", "ogr")
    KRIG_TEMP_POINT.setName("KRIG_TEMP_POINT")
    QgsProject.instance().addMapLayer(KRIG_TEMP_POINT)

else:
    # 결과 포인트 레이어 추가
    KRIG_TEMP_POINT = QgsVectorLayer(output_shp_path, "KRIG_TEMP_POINT", "ogr")
    KRIG_TEMP_POINT.setName("KRIG_TEMP_POINT")
    QgsProject.instance().addMapLayer(KRIG_TEMP_POINT)





# 11. 포인트 레이어에 공간 인덱스 생성
print("11. Create Spacial Index on Point Layer")
provider = KRIG_TEMP_POINT.dataProvider()
if not provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
    print("공간 인덱스를 생성할 수 없습니다. 데이터 제공자가 지원하지 않습니다.")
else:
    if provider.createSpatialIndex():
        print("공간 인덱스가 성공적으로 생성되었습니다.")
    else:
        print("공간 인덱스 생성에 실패하였습니다.")

        

qgs.exitQgis()