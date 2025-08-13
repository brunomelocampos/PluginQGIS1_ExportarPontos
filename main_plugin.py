from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl, QProcess
from qgis.PyQt import uic
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsWkbTypes,
    QgsUnitTypes,
    QgsRasterLayer,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsPointXY,
    QgsGeometry
)
from qgis import processing

import os
import math
import webbrowser

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "exportar_pontos.ui"))

class ExportarPontosDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class ExportarPontosPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None
        # Conecta os sinais do projeto
        QgsProject.instance().layersAdded.connect(self.atualizar_campos)
        QgsProject.instance().layersRemoved.connect(self.atualizar_campos)
        QgsProject.instance().cleared.connect(self.atualizar_campos)

    def initGui(self):
        icone_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icone_path), "Exportar Pontos para TXT", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Exportar Pontos", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&Exportar Pontos", self.action)
        self.iface.removeToolBarIcon(self.action)
        # Desconecta os sinais ao descarregar o plugin
        try:
            QgsProject.instance().layersAdded.disconnect(self.atualizar_campos)
            QgsProject.instance().layersRemoved.disconnect(self.atualizar_campos)
            QgsProject.instance().cleared.disconnect(self.atualizar_campos)
        except:
            pass

    def run(self):
        if not self.dlg:
            self.dlg = ExportarPontosDialog()
            self.setup()
            # Conecta o sinal de destruição da janela para limpar referências
            self.dlg.destroyed.connect(self.limpar_referencias)

        self.dlg.show()
        # Atualiza os campos sempre que a janela é aberta
        self.atualizar_campos()

    def limpar_referencias(self):
        """Limpa referências quando a janela é fechada"""
        self.dlg = None

    def setup(self):
        self.dlg.cmbCamada.clear()
        self.dlg.cmbNome.clear()
        self.dlg.cmbZ.clear()
        self.dlg.cmbDEM.clear()
        self.dlg.comboBoxDesc.clear()
        self.dlg.cmbSeparadorDecimal.clear()
        self.dlg.cmbPrecisao.clear()

        self.dlg.btnSelecionarArquivo.clicked.connect(self.selecionar_arquivo)
        self.dlg.buttonBox.accepted.disconnect()
        self.dlg.buttonBox.accepted.connect(self.exportar_sem_fechar)

        self.dlg.buttonBox.helpRequested.connect(self.show_help)

        # Conecta a mudança de camada para atualizar campos automaticamente
        self.dlg.cmbCamada.currentIndexChanged.connect(self.preencher_campos)
        
        # Configurações iniciais
        self.dlg.radioGeometria.setChecked(True)
        self.dlg.radioGeometria.toggled.connect(self.toggle_z_field)
        self.dlg.radioDEM.toggled.connect(self.toggle_dem_options)
        self.dlg.radioCampo.toggled.connect(self.toggle_z_field)

        self.dlg.cmbSeparadorDecimal.addItems(["Ponto", "Vírgula"])
        self.dlg.cmbPrecisao.addItems(["Precisão Natural", "Precisão Arredondada", "Precisão Truncada"])
        self.dlg.cmbPrecisao.currentIndexChanged.connect(self.toggle_precisao)
        self.toggle_precisao()

        # Preenche os campos iniciais
        self.atualizar_campos()

    def exportar_sem_fechar(self):
        self.exportar()  # reaproveita o método existente sem fechar o diálogo



    def atualizar_campos(self):
        """Atualiza todas as listas de camadas e campos"""
        if not self.dlg:
            return
            
        # Bloqueia sinais temporariamente para evitar múltiplas atualizações
        self.dlg.cmbCamada.blockSignals(True)
        self.dlg.cmbDEM.blockSignals(True)
        
        # Salva a seleção atual
        camada_selecionada = self.dlg.cmbCamada.currentData()
        dem_selecionado = self.dlg.cmbDEM.currentData()
        
        # Limpa e preenche as comboboxes
        self.dlg.cmbCamada.clear()
        self.dlg.cmbDEM.clear()
        
        # Preenche camadas vetoriais
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.dlg.cmbCamada.addItem(layer.name(), layer.id())
            if isinstance(layer, QgsRasterLayer):
                self.dlg.cmbDEM.addItem(layer.name(), layer.id())
        
        # Restaura a seleção anterior se ainda existir
        if camada_selecionada:
            index = self.dlg.cmbCamada.findData(camada_selecionada)
            if index >= 0:
                self.dlg.cmbCamada.setCurrentIndex(index)
        
        if dem_selecionado:
            index = self.dlg.cmbDEM.findData(dem_selecionado)
            if index >= 0:
                self.dlg.cmbDEM.setCurrentIndex(index)
        
        # Libera os sinais novamente
        self.dlg.cmbCamada.blockSignals(False)
        self.dlg.cmbDEM.blockSignals(False)
        
        # Atualiza os campos da camada selecionada
        self.preencher_campos()

    

    def show_help(self):
        html_file = os.path.join(os.path.dirname(__file__), "help.html")
        # Abre o arquivo no navegador padrão do sistema
        try:
            webbrowser.open(html_file)
        except Exception as e:
            QMessageBox.critical(self.dlg, "Erro", f"Não foi possível abrir o arquivo de ajuda:\n{str(e)}")


    def preencher_campos(self):
        self.dlg.cmbNome.clear()
        self.dlg.cmbZ.clear()
        self.dlg.comboBoxDesc.clear()
        self.dlg.comboBoxDesc.addItem("")  # Adiciona opção em branco
        camada_id = self.dlg.cmbCamada.currentData()
        camada = QgsProject.instance().mapLayer(camada_id)
        if not camada:
            return

        # Create spatial index for the input layer
        processing.run("native:createspatialindex", {'INPUT': camada})
        
        # Enable/disable Z from geometry based on layer type and Z dimension
        has_z = QgsWkbTypes.hasZ(camada.wkbType())
        self.dlg.radioGeometria.setEnabled(has_z)
        if not has_z and self.dlg.radioGeometria.isChecked():
            self.dlg.radioDEM.setChecked(True)

        for field in camada.fields():
            self.dlg.cmbNome.addItem(field.name())
            self.dlg.comboBoxDesc.addItem(field.name())
            if field.typeName().lower() in ['integer', 'double', 'real', 'float']:
                self.dlg.cmbZ.addItem(field.name())

    def preencher_rasters(self):
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                self.dlg.cmbDEM.addItem(layer.name(), layer.id())

    def toggle_z_field(self):
        self.dlg.cmbZ.setEnabled(self.dlg.radioCampo.isChecked())

    def toggle_dem_options(self):
        if self.dlg.radioDEM.isChecked():
            self.dlg.cmbDEM.setEnabled(True)
            self.dlg.cmbZ.setEnabled(False)
        else:
            self.dlg.cmbDEM.setEnabled(False)
            self.dlg.cmbZ.setEnabled(self.dlg.radioCampo.isChecked())

    def toggle_precisao(self):
        self.dlg.spinPrecisao.setEnabled(self.dlg.cmbPrecisao.currentText() != "Precisão Natural")

    def selecionar_arquivo(self):
        path, _ = QFileDialog.getSaveFileName(self.dlg, "Salvar como", "", "TXT Files (*.txt)")
        if path:
            self.dlg.txtCaminho.setText(path)

    def format_value(self, value, precisao_tipo, precisao_casas, separador):
        if precisao_tipo == "Precisão Natural":
            return str(value).replace(".", separador)

        if precisao_tipo == "Precisão Arredondada":
            val = round(value, precisao_casas)
            val_str = f'{val:.{precisao_casas}f}'
            return val_str.replace(".", separador)

        if precisao_tipo == "Precisão Truncada":
            s = str(value)
            if '.' in s:
                integer_part, decimal_part = s.split('.')
                if len(decimal_part) > precisao_casas:
                    decimal_part = decimal_part[:precisao_casas]
                else:
                    decimal_part = decimal_part.ljust(precisao_casas, '0')
                return f"{integer_part}{separador}{decimal_part}"
            else:
                return f"{s}{separador}{'0' * precisao_casas}"
        return str(value).replace(".", separador) # Fallback

    def exportar(self):
        caminho = self.dlg.txtCaminho.text()
        if not caminho:
            QMessageBox.warning(self.dlg, "Aviso", "Escolha o caminho do arquivo de saída.")
            return

        camada_id = self.dlg.cmbCamada.currentData()
        camada_original = QgsProject.instance().mapLayer(camada_id)
        if not camada_original:
            QMessageBox.critical(self.dlg, "Erro", "Camada inválida.")
            return

        # Create spatial index for the input layer
        processing.run("native:createspatialindex", {'INPUT': camada_original})

        # Process line/polygon layers by converting to points
        if camada_original.geometryType() in [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry]:
            # Extract vertices
            result = processing.run("native:extractvertices", {
                'INPUT': camada_original,
                'OUTPUT': 'memory:'
            })
            
            # Remove duplicate geometries
            result = processing.run("native:deleteduplicategeometries", {
                'INPUT': result['OUTPUT'],
                'OUTPUT': 'memory:'
            })
            
            # Use the processed layer
            camada = result['OUTPUT']
        else:
            camada = camada_original

        nome_campo = self.dlg.cmbNome.currentText()
        desc_campo = self.dlg.comboBoxDesc.currentText()
        incluir_desc = bool(desc_campo.strip())
        z_campo = self.dlg.cmbZ.currentText() if self.dlg.cmbZ.currentText() else None

        separador_decimal = "." if self.dlg.cmbSeparadorDecimal.currentText() == "Ponto" else ","
        precisao_tipo = self.dlg.cmbPrecisao.currentText()
        precisao_casas = self.dlg.spinPrecisao.value()

        if self.dlg.radioOrdemXY.isChecked():
            ordem = ["Nome", "Descricao", "X", "Y", "Z"] if incluir_desc else ["Nome", "X", "Y", "Z"]
        elif self.dlg.radioOrdemYX.isChecked():
            ordem = ["Nome", "Descricao", "Y", "X", "Z"] if incluir_desc else ["Nome", "Y", "X", "Z"]
        else:
            ordem = ["Nome", "X", "Y", "Z"]

        somente_selecionados = self.dlg.chkSelecionados.isChecked()
        feats = camada.selectedFeatures() if somente_selecionados else camada.getFeatures()

        crs_dest = self.dlg.widgetSRC.crs()
        transform = QgsCoordinateTransform(camada.crs(), crs_dest, QgsProject.instance())

        with open(caminho, 'w', encoding='utf-8') as f:
            f.write("\t".join(ordem) + "\n")


            total = camada.featureCount() if not somente_selecionados else len(feats)
            self.dlg.progressBar.setMinimum(0)
            self.dlg.progressBar.setMaximum(total)
            self.dlg.progressBar.setValue(0)



            for feat in feats:
                geom = feat.geometry()
                if geom.isEmpty():
                    continue

                # Transform the entire geometry first
                geom_transformada = QgsGeometry(geom)
                geom_transformada.transform(transform)
                
                # Get the point from transformed geometry
                point = geom_transformada.asPoint()

                # Handle field names differently for extracted vertices
                if camada_original.geometryType() in [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry]:
                    nome = str(feat['vertex_index']) if nome_campo == "" else str(feat[nome_campo]) if nome_campo in feat.fields().names() else ""
                    desc = str(feat[desc_campo]) if incluir_desc and desc_campo in feat.fields().names() else ""
                else:
                    nome = str(feat[nome_campo]) if nome_campo else ""
                    desc = str(feat[desc_campo]) if incluir_desc else ""

                x = self.format_value(point.x(), precisao_tipo, precisao_casas, separador_decimal)
                y = self.format_value(point.y(), precisao_tipo, precisao_casas, separador_decimal)

                if self.dlg.radioGeometria.isChecked():
                    if QgsWkbTypes.hasZ(geom.wkbType()):
                        # Get Z value from original geometry
                        point_original = geom.constGet()
                        if hasattr(point_original, 'z'):
                            z_val = point_original.z()
                        else:
                            z_val = 0
                    else:
                        z_val = 0
                    z = self.format_value(z_val, precisao_tipo, precisao_casas, separador_decimal)
                elif self.dlg.radioDEM.isChecked():
                    # Use original point (before transformation) to sample DEM
                    point_original = geom.asPoint()
                    z = self.get_z_from_raster(point_original, camada.crs())
                    if z != "NoData":
                        z = self.format_value(float(z), precisao_tipo, precisao_casas, separador_decimal)
                    else:
                        z = "NoData"
                elif self.dlg.radioCampo.isChecked():
                    if z_campo and z_campo in feat.fields().names() and feat[z_campo] is not None:
                        try:
                            z_val = float(feat[z_campo])
                        except:
                            z_val = 0
                    else:
                        z_val = 0
                    z = self.format_value(z_val, precisao_tipo, precisao_casas, separador_decimal)
                else:
                    z = "NoData"

                dados = {
                    "Nome": nome,
                    "Descricao": desc,
                    "X": x,
                    "Y": y,
                    "Z": z
                }

                linha_ordenada = [dados[coluna] for coluna in ordem]
                f.write("\t".join(linha_ordenada) + "\n")
                
                self.dlg.progressBar.setValue(self.dlg.progressBar.value() + 1)
                QApplication.processEvents()  # Força a UI a atualizar
            self.dlg.progressBar.setValue(0)
    

        # Remove temporary layer if it was created
        if camada != camada_original:
            QgsProject.instance().removeMapLayer(camada)

        QMessageBox.information(self.dlg, "Sucesso", "Arquivo exportado com sucesso!")

    def get_z_from_raster(self, point, src_crs):
        raster_layer_id = self.dlg.cmbDEM.currentData()
        raster_layer = QgsProject.instance().mapLayer(raster_layer_id)
        if isinstance(raster_layer, QgsRasterLayer):
            # Create a QgsPointXY from the point
            point_xy = QgsPointXY(point)
            
            transform = QgsCoordinateTransform(src_crs, raster_layer.crs(), QgsProject.instance())
            try:
                # Transform the QgsPointXY
                point_transformed = transform.transform(point_xy)
                
                value, res = raster_layer.dataProvider().sample(point_transformed, 1)
                if res:
                    return str(value)
            except:
                return "NoData"
        return "NoData"

