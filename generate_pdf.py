#!/usr/bin/env python3
"""
Generate Biology Notes PDF using raw PDF generation (no external libraries).
Covers: Flores/Plantae, Reino Fungi, Evolucion Autores y Teorias, Examen.
"""
import struct, zlib, os

class PDFWriter:
    """Minimal PDF writer supporting text, colors, rectangles, and multiple pages."""
    def __init__(self):
        self.objects = []
        self.pages = []
        self.current_stream = []
        self.page_width = 612  # letter
        self.page_height = 792
        self.margin_left = 45
        self.margin_right = 45
        self.margin_top = 50
        self.margin_bottom = 50
        self.y = self.page_height - self.margin_top
        self.fonts = {}
        self._setup_fonts()

    def _setup_fonts(self):
        self.fonts = {
            'Helvetica': 'F1',
            'Helvetica-Bold': 'F2',
            'Helvetica-Oblique': 'F3',
        }

    def _usable_width(self):
        return self.page_width - self.margin_left - self.margin_right

    def new_page(self):
        if self.current_stream:
            self.pages.append(self.current_stream)
        self.current_stream = []
        self.y = self.page_height - self.margin_top

    def _check_space(self, needed):
        if self.y - needed < self.margin_bottom:
            self.new_page()

    def set_color(self, r, g, b):
        self.current_stream.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def set_stroke_color(self, r, g, b):
        self.current_stream.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def draw_rect(self, x, y, w, h, fill=True, stroke=False):
        ops = []
        if fill and stroke:
            ops.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re B")
        elif fill:
            ops.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re f")
        elif stroke:
            ops.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re S")
        self.current_stream.extend(ops)

    def draw_text(self, x, y, text, font='Helvetica', size=10):
        fn = self.fonts.get(font, 'F1')
        escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        self.current_stream.append(f"BT /{fn} {size} Tf {x:.1f} {y:.1f} Td ({escaped}) Tj ET")

    def draw_line(self, x1, y1, x2, y2, width=0.5):
        self.current_stream.append(f"{width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")

    def add_banner(self, text, r, g, b, height=22, font_size=12):
        self._check_space(height + 8)
        x = self.margin_left
        w = self._usable_width()
        self.set_color(r, g, b)
        self.draw_rect(x, self.y - height, w, height, fill=True)
        self.set_color(1, 1, 1)
        self.draw_text(x + 8, self.y - height + (height - font_size) / 2 + 2, text, 'Helvetica-Bold', font_size)
        self.set_color(0, 0, 0)
        self.y -= height + 6

    def add_sub_banner(self, text, r, g, b):
        self.add_banner(text, r, g, b, height=18, font_size=10)

    def add_paragraph(self, text, font='Helvetica', size=9, indent=0, color=(0,0,0)):
        lines = self._wrap_text(text, font, size, self._usable_width() - indent)
        for line in lines:
            self._check_space(size + 3)
            self.set_color(*color)
            self.draw_text(self.margin_left + indent, self.y - size, line, font, size)
            self.y -= size + 3
        self.set_color(0, 0, 0)

    def add_bullet(self, text, level=1, size=9):
        prefix = "  * " if level == 1 else "    - "
        indent = 10 if level == 1 else 22
        self.add_paragraph(prefix + text, 'Helvetica', size, indent)

    def add_kv(self, key, val, size=9):
        full = f"{key}: {val}"
        lines = self._wrap_text(full, 'Helvetica', size, self._usable_width() - 8)
        for i, line in enumerate(lines):
            self._check_space(size + 3)
            if i == 0:
                # Draw key in bold, val in regular
                key_w = self._text_width(key + ": ", 'Helvetica-Bold', size)
                self.draw_text(self.margin_left + 8, self.y - size, key + ": ", 'Helvetica-Bold', size)
                rest = line[len(key) + 2:]
                self.draw_text(self.margin_left + 8 + key_w, self.y - size, rest, 'Helvetica', size)
            else:
                self.draw_text(self.margin_left + 14, self.y - size, line, 'Helvetica', size)
            self.y -= size + 3

    def add_spacer(self, h=8):
        self.y -= h

    def add_hr(self):
        self._check_space(6)
        self.set_stroke_color(0.7, 0.7, 0.7)
        self.draw_line(self.margin_left, self.y, self.page_width - self.margin_right, self.y, 0.5)
        self.set_stroke_color(0, 0, 0)
        self.y -= 6

    def add_cover(self, title, subtitles, r, g, b):
        h = 160
        x = self.margin_left
        w = self._usable_width()
        self.set_color(r, g, b)
        self.draw_rect(x, self.y - h, w, h, fill=True)
        self.set_color(1, 1, 1)
        tw = self._text_width(title, 'Helvetica-Bold', 22)
        self.draw_text(x + (w - tw) / 2, self.y - 40, title, 'Helvetica-Bold', 22)
        self.set_color(0.8, 0.88, 1.0)
        for i, sub in enumerate(subtitles):
            sw = self._text_width(sub, 'Helvetica', 10)
            self.draw_text(x + (w - sw) / 2, self.y - 70 - i * 15, sub, 'Helvetica', 10)
        self.set_color(0, 0, 0)
        self.y -= h + 20

    def add_table(self, headers, rows, col_widths, header_color=(0.1, 0.2, 0.5)):
        row_height = 14
        total_h = (len(rows) + 1) * row_height + 4
        self._check_space(min(total_h, 200))
        x = self.margin_left
        # Header
        total_w = sum(col_widths)
        self.set_color(*header_color)
        self.draw_rect(x, self.y - row_height, total_w, row_height, fill=True)
        self.set_color(1, 1, 1)
        cx = x
        for i, h in enumerate(headers):
            self.draw_text(cx + 3, self.y - row_height + 3, h[:int(col_widths[i]/5)], 'Helvetica-Bold', 8)
            cx += col_widths[i]
        self.y -= row_height
        # Rows
        for ri, row in enumerate(rows):
            self._check_space(row_height + 2)
            if ri % 2 == 1:
                self.set_color(0.95, 0.95, 0.95)
                self.draw_rect(x, self.y - row_height, total_w, row_height, fill=True)
            self.set_color(0, 0, 0)
            cx = x
            for i, cell in enumerate(row):
                truncated = cell.replace('\n', ' ')[:int(col_widths[i]/4.5)]
                self.draw_text(cx + 3, self.y - row_height + 3, truncated, 'Helvetica', 7.5)
                cx += col_widths[i]
            # grid
            self.set_stroke_color(0.8, 0.8, 0.8)
            self.draw_line(x, self.y - row_height, x + total_w, self.y - row_height, 0.3)
            self.set_stroke_color(0, 0, 0)
            self.y -= row_height
        self.y -= 6

    def _text_width(self, text, font, size):
        # Approximate: Helvetica avg char width ~ 0.52 * size
        factor = 0.54 if 'Bold' in font else 0.52
        return len(text) * size * factor

    def _wrap_text(self, text, font, size, max_width):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if self._text_width(test, font, size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines if lines else [""]

    def save(self, filename):
        if self.current_stream:
            self.pages.append(self.current_stream)

        # Build PDF
        objs = []
        obj_offsets = []

        # Obj 1: Catalog
        objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Obj 2: Pages (placeholder, will fix)
        page_obj_start = 4  # fonts at 3
        kids = " ".join([f"{page_obj_start + i*2} 0 R" for i in range(len(self.pages))])
        objs.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>\nendobj\n".encode())

        # Obj 3: Font resources
        objs.append(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        # We need separate objects for each font
        # Let's reorganize: obj3=F1(Helv), obj4=F2(Helv-Bold), obj5=F3(Helv-Oblique)
        # Then pages start at obj 6

        # Redo
        objs = []
        objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")  # 1

        page_obj_start = 6
        kids = " ".join([f"{page_obj_start + i*2} 0 R" for i in range(len(self.pages))])
        objs.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>\nendobj\n".encode())  # 2

        objs.append(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n")  # 3
        objs.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n")  # 4
        objs.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>\nendobj\n")  # 5

        resources = "/Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >>"

        # Pages and streams
        obj_num = 6
        for page_stream_cmds in self.pages:
            stream_content = "\n".join(page_stream_cmds).encode('latin-1', errors='replace')
            stream_len = len(stream_content)

            # Page object
            page_obj = f"{obj_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.page_width} {self.page_height}] /Contents {obj_num+1} 0 R /Resources << {resources} >> >>\nendobj\n"
            objs.append(page_obj.encode())
            obj_num += 1

            # Stream object
            stream_obj = f"{obj_num} 0 obj\n<< /Length {stream_len} >>\nstream\n".encode() + stream_content + b"\nendstream\nendobj\n"
            objs.append(stream_obj)
            obj_num += 1

        # Write file
        with open(filename, 'wb') as f:
            f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            offset = f.tell()
            offsets = []
            for i, obj in enumerate(objs):
                offsets.append(f.tell())
                f.write(obj)

            xref_pos = f.tell()
            f.write(b"xref\n")
            f.write(f"0 {len(objs)+1}\n".encode())
            f.write(b"0000000000 65535 f \n")
            for off in offsets:
                f.write(f"{off:010d} 00000 n \n".encode())
            f.write(b"trailer\n")
            f.write(f"<< /Size {len(objs)+1} /Root 1 0 R >>\n".encode())
            f.write(b"startxref\n")
            f.write(f"{xref_pos}\n".encode())
            f.write(b"%%EOF\n")

        return filename



# Color definitions (RGB 0-1)
C_FLORES = (0.533, 0.055, 0.310)      # #880e4f
C_FLORES_S = (0.761, 0.094, 0.357)    # #c2185b
C_FUNGI = (0.290, 0.078, 0.549)       # #4a148c
C_FUNGI_S = (0.482, 0.122, 0.635)     # #7b1fa2
C_AUTORES = (0.106, 0.369, 0.125)     # #1b5e20
C_AUTORES_S = (0.180, 0.490, 0.196)   # #2e7d32
C_DARK = (0.051, 0.231, 0.431)        # #0d3b6e
C_RED = (0.718, 0.110, 0.110)         # #b71c1c


def build_document():
    pdf = PDFWriter()

    # === COVER PAGE ===
    pdf.add_cover('APUNTES DE BIOLOGIA', [
        'Las Flores & Plantas Vasculares',
        'Reino Fungi',
        'Evolucion: Autores y Teorias',
        'Examen Integrador'
    ], *C_DARK)
    pdf.add_paragraph('Este documento contiene apuntes de clase + examen integrador.', 'Helvetica', 9, 0)
    pdf.add_paragraph('Contenido basado fielmente en los PDFs originales de clase.', 'Helvetica', 9, 0)
    pdf.new_page()

    # ============================================================
    # SECCION 1: LAS FLORES / REINO PLANTAE
    # ============================================================
    pdf.add_cover('REINO PLANTAE - LAS FLORES', [
        'Tipos de flores - Partes - Formacion de semilla',
        'Plantas vasculares - Raiz - Tallo - Hojas',
        'Frutos - Clasificaciones - Hormonas - Adaptaciones'
    ], *C_FLORES)
    pdf.add_spacer(12)

    pdf.add_banner('LAS FLORES', *C_FLORES)
    pdf.add_paragraph('Organos reproductores de las plantas cuyo objetivo fue atraer a los insectos (y uno que otro "zonzo humano" que posiblemente las plantas no pretendian).')
    pdf.add_spacer(6)

    pdf.add_sub_banner('Tipos de Flores', *C_FLORES_S)
    pdf.add_table(
        ['Tipo', 'Descripcion', 'Ejemplos'],
        [
            ['FLOR PERFECTA (hermafrodita)', 'Aparato reproductor fem. Y masc. en la misma flor', 'Manzano, tomate, rosa'],
            ['FLOR IMPERFECTA Monoica', 'Flores masc. separadas de fem., misma planta', 'Maiz, calabaza'],
            ['FLOR IMPERFECTA Dioica', 'Sexos separados en distintas plantas', 'Papaya, espinaca'],
        ],
        [150, 220, 130], header_color=C_FLORES
    )

    pdf.add_banner('PARTES DE LA FLOR PERFECTA', *C_FLORES)
    pdf.add_sub_banner('Gineceo (parte femenina)', *C_FLORES_S)
    pdf.add_kv('Arqueogonios', 'Estructuras femeninas')
    pdf.add_kv('Pistilo / Carpelo', 'Incluye estigma, estilo y ovario')
    pdf.add_kv('Ovulos', 'Se encuentran dentro del ovario')

    pdf.add_sub_banner('Androceo (parte masculina - Estambres)', *C_FLORES_S)
    pdf.add_kv('Antera / Tecas', 'Estructura que contiene los granos de polen')
    pdf.add_kv('Filamento', 'Sostiene la antera')
    pdf.add_kv('Conectivo', 'Une las dos tecas de la antera')

    pdf.add_sub_banner('Perianto', *C_FLORES_S)
    pdf.add_kv('Corola / Petalos', 'Conjunto de petalos - funcion de atraccion')
    pdf.add_kv('Caliz / Sepalos', 'Petalos en la base - proteccion del boton floral')
    pdf.add_kv('Pedicelo', 'Tallo de la flor')
    pdf.add_kv('Nectario', 'Produce nectar para atraer polinizadores')
    pdf.add_spacer()

    pdf.add_banner('EL POLEN', *C_FLORES)
    pdf.add_bullet('Un grano de polen es el gametofito masculino en estado inmaduro.')
    pdf.add_bullet('Para terminar su maduracion debe caer en el estigma de la flor.')
    pdf.add_bullet('El gametofito maduro formara dos espermatozoides.')
    pdf.add_spacer()

    pdf.add_banner('FORMACION DE LA SEMILLA', *C_FLORES)
    pdf.add_kv('Embrion', 'Se desarrolla de la fecundacion de la celula huevo (n+n)')
    pdf.add_kv('Endosperma', 'Se forma de la celula 3n - reserva alimenticia de la semilla')
    pdf.add_kv('Cubierta de la semilla', 'La forma el gametofito femenino')
    pdf.add_kv('Fruto', 'Se forma del ovario y del carpelo')
    pdf.add_paragraph('Germinacion: Cuando la semilla absorbe agua, se produce giberelina que llega a la capa aleucrona para formar enzimas que hidrolizan el endosperma y originan nutrientes para la futura plantula.', 'Helvetica', 9)
    pdf.add_spacer()

    pdf.add_banner('PLANTAS VASCULARES', *C_FLORES)
    pdf.add_paragraph('Vastago: cuerpo de la planta exceptuando la raiz.', 'Helvetica-Bold', 9)

    pdf.add_sub_banner('RAIZ', *C_FLORES_S)
    pdf.add_kv('Primera raiz (embrionaria)', 'Se llama radicula')
    pdf.add_kv('Funcion', 'Fijacion y absorcion de nutrientes')
    pdf.add_kv('Sin cloroplastos', 'No realiza fotosintesis - si tiene leucoplastos para almacenar nutrientes')
    pdf.add_paragraph('Estructura basica:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Tejido epidermico -> epidermis')
    pdf.add_bullet('Tejido fundamental -> corteza')
    pdf.add_bullet('Tejido vascular -> cilindro central')
    pdf.add_paragraph('Capas internas:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Protodermis -> recubrimiento')
    pdf.add_bullet('Meristema fundamental -> relleno')
    pdf.add_bullet('Suberina / Cutina -> impermeabilizacion')
    pdf.add_bullet('Banda de Caspari -> barrera selectiva de absorcion')
    pdf.add_bullet('Periciclo -> origina raices laterales en dicotiledoneas')
    pdf.add_bullet('CALIPTRA -> estructura protectora de la punta de la raiz')

    pdf.add_sub_banner('Crecimiento de la Raiz', *C_FLORES_S)
    pdf.add_bullet('La radicula rompe la vaina seminal de la semilla.')
    pdf.add_bullet('DICOTILEDONEAS: raiz primaria que origina raices laterales del periciclo.')
    pdf.add_bullet('MONOCOTILEDONEAS: raices adventicias desde la base del tallo.')

    pdf.add_sub_banner('Absorcion del Agua', *C_FLORES_S)
    pdf.add_bullet('Celulas de raices son hiperosmooticas - osmosis ingresa el agua.')
    pdf.add_bullet('El agua avanza por simplasto o apoplasto hasta la banda de Caspary.')
    pdf.add_bullet('El agua en el cilindro central viaja por xilema = savia bruta.')
    pdf.add_bullet('Presion de raiz: presion positiva que crea columna de agua.')
    pdf.add_bullet('Transpiracion arriba genera presion negativa que succiona agua.')

    pdf.add_sub_banner('Absorcion de Elementos Esenciales', *C_FLORES_S)
    pdf.add_bullet('Minerales liberados de rocas por liquenes; micorrizas ayudan absorcion.')
    pdf.add_bullet('Iones necesarios para formacion de azucares en fotosintesis.')
    pdf.add_bullet('Nitrogeno: bacterias nitrificantes lo fijan al suelo como nitratos.')
    pdf.add_spacer()


    pdf.add_sub_banner('TALLO', *C_FLORES_S)
    pdf.add_bullet('Portan las hojas y transportan sustancias raices<->hojas.')
    pdf.add_bullet('Tienen celulas fotosinteticas.')
    pdf.add_table(
        ['Tejido Vascular', 'Celulas', 'Funcion'],
        [
            ['XILEMA', 'Traqueadas -> vasos', 'Savia bruta (agua+sales) hacia arriba'],
            ['FLOEMA', 'Celulas cribosas -> tubos', 'Savia elaborada (azucares+nutrientes)'],
        ],
        [120, 180, 200], header_color=C_FLORES
    )
    pdf.add_paragraph('Crecimiento del Tallo:', 'Helvetica-Bold', 9)
    pdf.add_bullet('PRIMARIO: meristema primario (gemas apicales) - crece a lo alto.')
    pdf.add_bullet('SECUNDARIO: meristemas secundarios (axilares) - hojas y ramas.')
    pdf.add_bullet('AUXINA inhibe crecimiento lateral; CITOCININAS estimulan desde abajo.')
    pdf.add_paragraph('Estructuras especiales:', 'Helvetica-Bold', 9)
    pdf.add_kv('Estolon', 'Tallo aereo que genera nuevas plantas al alejarse')
    pdf.add_kv('Rizoma', 'Tallo subterraneo que genera nuevas plantas')
    pdf.add_kv('Esqueje', 'Fragmento de planta que al ser enterrado genera nueva planta')
    pdf.add_spacer()

    pdf.add_sub_banner('HOJAS', *C_FLORES_S)
    pdf.add_kv('Funcion', 'Estructuras fotosinteticas y de intercambio gaseoso')
    pdf.add_kv('Haz', 'Superficie superior de la hoja')
    pdf.add_kv('Enves', 'Parte inferior de la hoja')
    pdf.add_kv('Limbo', 'Orilla de la hoja')
    pdf.add_kv('Peciolo', 'Minitallo que une la hoja al tallo principal')
    pdf.add_paragraph('Modificaciones y Adaptaciones:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Hojas GRANDES para climas humedos.')
    pdf.add_bullet('Hojas CHICAS para climas secos.')
    pdf.add_bullet('ESPINAS Y AGUIJONES como defensa.')
    pdf.add_bullet('Hojas de CONIFERAS (perennes): adaptadas para evitar perdida de agua.')
    pdf.add_spacer()

    pdf.add_banner('TIPOS DE FRUTOS', *C_FLORES)
    pdf.add_table(
        ['Categoria', 'Tipo', 'Descripcion', 'Ejemplos'],
        [
            ['SECOS', 'Dehiscentes', 'Se abre y libera semillas SIN desprenderse', '-'],
            ['SECOS', 'Indehiscentes', 'Encierra semillas y SE libera de la planta', '-'],
            ['CARNOSOS', 'Drupas', 'Frutos con UNA sola semilla', 'Mango, cereza'],
            ['CARNOSOS', 'Bayas', 'Una o varias semillas con pulpa jugosa', 'Tomate, uva'],
            ['CARNOSOS', 'Pomes', 'Estructura central con tejido carnoso', 'Manzana, pera'],
            ['COMPUESTOS', 'Agregados', 'Varios carpelos de UNA flor', 'Frambuesa, fresa'],
            ['COMPUESTOS', 'Multiples', 'Carpelos de FLORES SEPARADAS', 'Pina, higo'],
        ],
        [80, 85, 200, 120], header_color=C_FLORES
    )

    pdf.add_banner('CLASIFICACIONES ALIMENTARIAS DE LAS PLANTAS', *C_FLORES)
    pdf.add_table(
        ['Clasificacion', 'Descripcion', 'Ejemplos'],
        [
            ['LEGUMBRES', 'Semillas comestibles familia FABACEAE', 'Lentejas, frijol, chicharo'],
            ['HORTALIZAS', 'Partes de plantas verdes comestibles', 'Espinaca, lechuga, brocoli'],
            ['TUBERCULOS', 'Raices comestibles', 'Papa, zanahoria, camote'],
            ['BULBO', 'Tallos subterraneos abombados', 'Cebolla, ajo'],
            ['FRUTAS', 'Ovarios de frutos indehiscentes', 'Manzana, naranja, platano'],
            ['GRAMINEAS', 'Plantas adaptables a vida salvaje', 'Pastizales, praderas'],
            ['CEREALES', 'Semillas de las gramineas', 'Trigo, maiz, arroz'],
        ],
        [110, 220, 170], header_color=C_FLORES
    )
    pdf.add_spacer()


    pdf.add_banner('HORMONAS DE LAS PLANTAS', *C_FLORES)

    pdf.add_sub_banner('1. AUXINAS (Acido Indolacetico / AIA)', *C_FLORES_S)
    pdf.add_paragraph('DOMINANCIA APICAL:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Crecimiento de la punta de la planta.')
    pdf.add_bullet('Yemas axilares inhibidas por auxinas si el apice esta cerca.')
    pdf.add_bullet('Al alejarse, citocininas provocan crecimiento de ramas/hojas.')
    pdf.add_paragraph('CRECIMIENTO DE FRUTOS:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Sin auxinas los frutos no crecen.')
    pdf.add_bullet('Maduracion final depende del etileno.')
    pdf.add_paragraph('GEOTROPISMO O GRAVITROPISMO:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Respuesta a la gravedad; tallos y raices crecen en sus direcciones.')
    pdf.add_bullet('Se percibe por estatolitos en amiloplastos en la punta de raices.')
    pdf.add_paragraph('FOTOTROPISMO:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Crecimiento asimetrico para buscar la luz.')
    pdf.add_paragraph('HELIOTROPISMO:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Capacidad de seguir el movimiento diurno del sol.')
    pdf.add_paragraph('CIRCUNMUTACION Y TIGOTROPISMO:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Circunmutacion: la planta explora su alrededor.')
    pdf.add_bullet('Tigotropismo: respuesta al tocar una superficie.')
    pdf.add_paragraph('TIGMONASTIA O SEISMONASTIA:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Movimiento mediante el tacto. Ej: Mimosa pudica.')

    pdf.add_sub_banner('2. CITOCININAS', *C_FLORES_S)
    pdf.add_bullet('Estimulan la mitosis.')
    pdf.add_bullet('En tejidos en division: meristemas, semillas, frutos, raices.')
    pdf.add_bullet('Evitan la senescencia de las plantas.')
    pdf.add_bullet('La mas activa se llama ZEATINA.')

    pdf.add_sub_banner('3. ETILENO', *C_FLORES_S)
    pdf.add_bullet('Hormona gaseosa - a temperatura ambiente es un gas.')
    pdf.add_bullet('Cambia color, textura y composicion quimica del fruto.')
    pdf.add_bullet('Auxinas favorecen produccion de etileno en yemas axilares.')
    pdf.add_bullet('Cuando auxinas desaparecen, causan caida de hojas en caducas.')
    pdf.add_spacer()

    pdf.add_banner('ADAPTACION A LAS ESTACIONES', *C_FLORES)
    pdf.add_bullet('Semillas pueden entrar en dormicion o latencia.')
    pdf.add_bullet('La viabilidad disminuye con el tiempo.')
    pdf.add_bullet('Dormicion desaparece cuando cubierta se rompe o ablanda.')
    pdf.add_kv('Longevidad', 'Anuales (1 ano), bienales (2 anos) o perennes (siempre con hojas)')
    pdf.add_kv('Fotoperiocidad', 'Conteo de luz/oscuridad para prever lluvias, sequias, estaciones')
    pdf.add_spacer()

    pdf.add_banner('PROTECCION EN PLANTAS', *C_FLORES)
    pdf.add_bullet('Sustancias quimicas: alcaloides, flavonoides, terpenoides (antimicrobianas).')
    pdf.add_bullet('Metil jasmonato liberado al aire para alertar a otras plantas.')
    pdf.add_bullet('Taninos para disuadir herbivoros.')
    pdf.add_paragraph('Plantas Carnivoras:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Drosera: tentaculos con sustancia mucilaginosa que atrapa insectos.')
    pdf.add_bullet('Nepenthes: atrapan insectos con nectar causando su caida.')

    pdf.new_page()


    # ============================================================
    # SECCION 2: REINO FUNGI
    # ============================================================
    pdf.add_cover('REINO FUNGI', [
        'Caracteristicas - Reproduccion - Grupos principales',
        'Enfermedades - Relaciones simbioticas',
        'Micorrizas - Liquenes - Introduccion a Plantae'
    ], *C_FUNGI)
    pdf.add_spacer(12)

    pdf.add_banner('CARACTERISTICAS GENERALES DEL REINO FUNGI', *C_FUNGI)
    pdf.add_kv('Tipo celular', 'Multicelulares eucariotas, heterotrofos e inmoviles')
    pdf.add_kv('Pared celular', 'QUITINA')
    pdf.add_kv('Reserva alimenticia', 'GLUCOGENO')
    pdf.add_kv('Modo de vida', 'Saprofitos, parasitos facultativos/obligados, simbiontes')
    pdf.add_kv('Nutricion', 'Secretan enzimas digestivas al exterior -> OSMOTROFIA')
    pdf.add_kv('Rol ecologico', 'Principales descomponedores de materia organica (con bacterias)')
    pdf.add_kv('Ribosomas', '80S')
    pdf.add_kv('Vacuolas', 'Hacen funcion de lisosomas')
    pdf.add_kv('Centriolos', 'La mayoria carece de centriolos; ningun hongo fagocita')
    pdf.add_kv('Cloroplastos', 'No tienen')

    pdf.add_sub_banner('Importancia economica e industrial', *C_FUNGI_S)
    pdf.add_bullet('Utiles en: queso, vinos, cerveza, pan.')
    pdf.add_bullet('Comestibles: Agaricus bisporus (champinon), Shiitake.')
    pdf.add_bullet('Antibioticos: Penicillum.')
    pdf.add_spacer()

    pdf.add_banner('GRUPOS DEL REINO FUNGI', *C_FUNGI)
    pdf.add_table(
        ['Grupo', 'Estado', 'Reprod. Sexual', 'Reprod. Asexual'],
        [
            ['ASCOMICETOS', 'Mas especies', 'Ascosporas', 'Gemacion, conidios'],
            ['BASIDIOMICETOS', 'Hongos con sombrero', 'Basidiosporas', 'Gemacion, conidios, fragmentacion'],
            ['CIGOMICETOS', 'Saprofitos/parasitos', 'Cigosporas', 'Conidios anemofilos'],
            ['QUITRIDIOMICETOS', 'Acuaticos', 'Zoosporas', 'Conidios'],
            ['DEUTEROMICETOS', 'Ya no existen como grupo', 'Sin reprod. sexual', 'Conidios'],
        ],
        [110, 120, 120, 150], header_color=C_FUNGI
    )

    pdf.add_sub_banner('QUITRIDIOMICETOS - Detalle', *C_FUNGI_S)
    pdf.add_kv('Habitat', 'Generalmente acuaticos, saprofitos')
    pdf.add_kv('Parasitismo', 'Solo parasitan plantas o insectos')
    pdf.add_kv('Hifas', 'Cenociticas (sin tabiques)')
    pdf.add_kv('Gametos', 'Siempre flagelados = ZOOSPORAS')
    pdf.add_paragraph('Unicos hongos con celulas moviles en una etapa de vida.', 'Helvetica-Bold', 9)

    pdf.add_sub_banner('GLOMEROMYCETES - Detalle', *C_FUNGI_S)
    pdf.add_kv('Habitat', 'Hongos terrestres saprofitos o parasitos')
    pdf.add_kv('Hifas', 'Cenociticas')
    pdf.add_kv('Ejemplo', 'Moho negro del pan: Rhyzopus stolonifer')

    pdf.add_sub_banner('BASIDIOMICETOS - Detalle', *C_FUNGI_S)
    pdf.add_kv('Habitat', 'Hongos terrestres')
    pdf.add_kv('Hifas', 'Septadas con comunicaciones citoplasmaticas')
    pdf.add_kv('Estructura reproductora', 'Basidiocarpo (seta/hongo con sombrero)')
    pdf.add_kv('Micelio', 'Se extiende radicalmente; setas forman "anillos de bruja"')
    pdf.add_paragraph('Ejemplos: Amanita, Psilocibos, Huitlacoche, Agaricus, Shiitake.', 'Helvetica', 9)
    pdf.add_paragraph('Mas grande del mundo: Armillaria mellea.', 'Helvetica-Bold', 9)

    pdf.add_sub_banner('ASCOMICETOS - Detalle (mas especies)', *C_FUNGI_S)
    pdf.add_kv('Etimologia', 'ASKA = saco')
    pdf.add_kv('Incluye', 'Levaduras, trufas, colmenillas')
    pdf.add_kv('Hifas', 'Tabicadas con segmentos mononucleares')
    pdf.add_paragraph('LEVADURAS (unicelulares):', 'Helvetica-Bold', 9)
    pdf.add_bullet('Responsables de fermentacion de fruta y bebidas espirituosas.')
    pdf.add_bullet('Azucares + medio anaerobio -> Alcohol + CO2')
    pdf.add_paragraph('Ejemplos importantes:', 'Helvetica-Bold', 9)
    pdf.add_kv('Saccharomyces cerevisiae', 'Levadura de cerveza o pan')
    pdf.add_kv('Candida albicans', 'Levadura patogena')
    pdf.add_kv('Penicillum', 'Produce antibioticos')
    pdf.add_kv('Aspergillus', 'Oportunista - afecta pulmones, oidos, senos paranasales. Aflatoxinas.')
    pdf.add_kv('Ophiocordyceps', 'Hongo parasito de insectos (zombie fungus)')
    pdf.add_paragraph('ERGOTISMO: convulsiones y alucinaciones; causado por cornezuelo del centeno.', 'Helvetica-Bold', 9, 0, C_RED)
    pdf.add_paragraph('LSD viene del cornezuelo del centeno.', 'Helvetica', 9)
    pdf.add_spacer()


    pdf.add_sub_banner('DEUTEROMICETOS (Hongos Imperfectos)', *C_FUNGI_S)
    pdf.add_bullet('Agrupados dentro de Ascomicetos y Basidiomicetos asexuales.')
    pdf.add_bullet('No tienen reproduccion sexual = "imperfectos".')
    pdf.add_paragraph('Enfermedades por Deuteromicetos:', 'Helvetica-Bold', 9, 0, C_RED)
    pdf.add_kv('TINAS - Trychophyton', 'Se come el cabello (tinea capitis)')
    pdf.add_kv('TINAS - Dermatophyton', 'Se come la piel (tinea pedis, corporis)')
    pdf.add_kv('Malassezia furfur', 'Pitiriasis versicolor - manchas en la piel')
    pdf.add_kv('Histoplasma capsulatum', 'Histoplasmosis - infeccion pulmonar')
    pdf.add_kv('Coccidioides immitis', 'Coccidioidomicosis - infeccion respiratoria')
    pdf.add_spacer()

    pdf.add_banner('RELACIONES SIMBIOTICAS', *C_FUNGI)

    pdf.add_sub_banner('MICORRIZAS', *C_FUNGI_S)
    pdf.add_paragraph('Asociaciones entre hongos y raices de plantas vasculares.', 'Helvetica-Bold', 9)
    pdf.add_table(
        ['Tipo', 'Hongo', 'Estructura', 'Donde'],
        [
            ['Endomicorrizas', 'Cigomiceto', 'Hifas DENTRO de raiz (vesiculas/arbusculos)', 'Mayoria plantas'],
            ['Ectomicorrizas', 'Basidiomiceto/Ascomiceto', 'Hifas ALREDEDOR (vaina de Harting)', 'Pino, sauces'],
        ],
        [100, 120, 200, 80], header_color=C_FUNGI
    )
    pdf.add_paragraph('Beneficios: absorcion de agua, fosforo, cobre, zinc, resistencia a hongos patogenos.', 'Helvetica', 9)
    pdf.add_paragraph('Ectomicorrizas ADEMAS: absorben nitrogeno y conectan raices de arboles (Wood Wide Web).', 'Helvetica', 9)

    pdf.add_sub_banner('LIQUENES', *C_FUNGI_S)
    pdf.add_kv('Definicion', 'Asociacion hongo + alga verde O cianobacterias')
    pdf.add_kv('Habitat', 'Rocas, suelos y troncos')
    pdf.add_kv('Importancia', 'Inician formacion del suelo, preparandolo para musgos y plantas')
    pdf.add_table(
        ['Capa del Liquen', 'Descripcion'],
        [
            ['1. Cortex superior', 'Hojas protectoras gelatinizadas'],
            ['2. Capa algal', 'Algas verdes o cianobacterias (fotosintesis)'],
            ['3. Medula', 'Hifas gelatinizadas'],
            ['4. Cortex inferior', 'Proyecciones de fijacion al sustrato'],
        ],
        [150, 350], header_color=C_FUNGI
    )
    pdf.add_spacer()

    pdf.add_banner('INTRODUCCION AL REINO PLANTAE (desde tema Fungi)', *C_FUNGI)
    pdf.add_paragraph('Las plantas evolucionaron de algas verdes. Son organismos fotosinteticos multicelulares que evolucionaron para utilizar CO2 con estructuras que captaban nutrientes y agua.', 'Helvetica', 9)

    pdf.add_sub_banner('Sistemas de Tejidos en Plantas', *C_FUNGI_S)
    pdf.add_table(
        ['Sistema', 'Composicion'],
        [
            ['Crecimiento', 'Meristemas primarios y secundarios'],
            ['Fundamental', 'Parenquima (relleno), colenquima y esclerenquima (sosten)'],
            ['Epidermico', 'Epidermis (cubierta protectora); en cuerpo secundario -> peridermis'],
            ['Vascular', 'Xilema (agua y sales) y Floema (nutrientes elaborados)'],
        ],
        [120, 380], header_color=C_FUNGI
    )

    pdf.add_sub_banner('Reproduccion en Plantas', *C_FUNGI_S)
    pdf.add_table(
        ['Tipo', 'Nombre', 'Organo', 'Produce'],
        [
            ['SEXUAL', 'GAMETOFITO', 'Anteridio (masc) / Arqueogonio (fem)', 'Gametos'],
            ['ASEXUAL', 'ESPOROFITO', '-', 'Esporas asexuales'],
        ],
        [70, 100, 200, 130], header_color=C_FUNGI
    )

    pdf.add_sub_banner('Clasificacion General de Plantas', *C_FUNGI_S)
    pdf.add_table(
        ['Grupo', 'Tipo', 'Ejemplos'],
        [
            ['AVASCULARES', 'BRIOPHYTA (musgos)', 'Hepatopsida, Bryopsida, Anthoserotopsida'],
            ['VASCULARES SIN SEMILLA', 'Criptogamas vasculares', 'Helechos, licopodios'],
            ['VASCULARES CON SEMILLA', 'GIMNOSPERMAS', 'Semilla desnuda: pinos, cipreses'],
            ['VASCULARES CON SEMILLA', 'ANGIOSPERMAS', 'Con flor y fruto. Mono y dicotiledoneas'],
        ],
        [130, 140, 230], header_color=C_FUNGI
    )
    pdf.add_paragraph('Contexto: Las plantas con semillas aparecieron al final del Carbonifero. En el Permico solo las semillas sobrevivieron.', 'Helvetica', 9)

    pdf.new_page()


    # ============================================================
    # SECCION 3: AUTORES Y TEORIAS DE EVOLUCION
    # ============================================================
    pdf.add_cover('EVOLUCION: AUTORES Y TEORIAS', [
        'Genetica en la evolucion - Sintesis Evolutiva Moderna',
        'Equilibrio Hardy-Weinberg - Origen de los Reinos',
        'Personajes clave - Taxonomia - Especiacion'
    ], *C_AUTORES)
    pdf.add_spacer(12)

    pdf.add_banner('GENETICA EN LA EVOLUCION', *C_AUTORES)

    pdf.add_sub_banner('Theodosius Dobzhansky', *C_AUTORES_S)
    pdf.add_kv('Profesion', 'Genetista humano')
    pdf.add_kv('Frase celebre', '"En la biologia nada es logico si no se contempla a la luz de la evolucion"')
    pdf.add_kv('Aportacion', 'El primero que ordeno las especies por TIPO, no por caracteristicas exteriores')

    pdf.add_sub_banner('Ernst Mayr', *C_AUTORES_S)
    pdf.add_kv('Profesion', 'Medico biologo Aleman')
    pdf.add_kv('Aportacion', 'Apoyo la teoria de la Sintesis Evolutiva Moderna')

    pdf.add_sub_banner('SINTESIS EVOLUTIVA MODERNA (Neodarwinismo)', *C_AUTORES_S)
    pdf.add_kv('Fundadores', 'George Ledyard Stebbins y Ernst Mayr')
    pdf.add_paragraph('La evolucion es consecuencia de 3 hechos naturales:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Variabilidad genetica')
    pdf.add_bullet('Herencia de caracteres adquiridos')
    pdf.add_bullet('Seleccion natural')
    pdf.add_paragraph('Nota: Darwin hablo de seleccion natural solamente - NUNCA de evolucion como termino.', 'Helvetica-Bold', 9)

    pdf.add_sub_banner('EQUILIBRIO DE HARDY-WEINBERG', *C_AUTORES_S)
    pdf.add_paragraph('Si se cumplen estas 4 condiciones, NO hay evolucion:', 'Helvetica-Bold', 9)
    pdf.add_bullet('1. Grandes poblaciones')
    pdf.add_bullet('2. Apareamientos estocasticos (al azar)')
    pdf.add_bullet('3. No grandes migraciones ni endogamia')
    pdf.add_bullet('4. Ningun accidente mutacional')
    pdf.add_spacer()

    pdf.add_banner('ORIGEN DE LOS REINOS - HISTORIA DE LA CLASIFICACION', *C_AUTORES)
    pdf.add_table(
        ['Autor', 'Aportacion'],
        [
            ['Robert Brown', 'Descubridor del nucleo celular (1a organela descubierta)'],
            ['John Hogg', 'Prototicsia - unicelulares y bacterias juntos'],
            ['Ernst Haeckel', 'Dividio en 2 reinos: Protista y Monere'],
            ['Edward Chaton', 'Dividio entre: Procariota y Eucaria'],
            ['Herbert Copeland', 'Elevo Moneres a reino: Monera'],
            ['Robert Whittaker', 'Propuso el Reino Fungi como independiente'],
            ['Margulis + Whittaker', 'Agregaron algas al reino Protista'],
            ['Carl Woese', 'Propuso Dominios: Eukarya, Procaria, Archea'],
            ['1990 (consenso)', 'Eubacteria, Archebacteria, Protoctista, Fungi, Animal, Vegetal'],
        ],
        [150, 350], header_color=C_AUTORES
    )
    pdf.add_spacer()


    pdf.add_banner('EVOLUCION SISTEMATICA Y TAXONOMIA', *C_AUTORES)

    pdf.add_sub_banner('Definiciones clave', *C_AUTORES_S)
    pdf.add_kv('Taxonomia', 'Ciencia que clasifica a los organismos')
    pdf.add_kv('Sistematica', 'Area que clasifica especies en base a su historia evolutiva')
    pdf.add_kv('Taxon', 'Division o grupo definido por propositos de clasificacion')
    pdf.add_kv('Clado', 'Rama en la clasificacion comparativa entre especies')
    pdf.add_kv('Cladismo', 'Teoria: nuevas especies aparecen por caracteristicas inexistentes hereditarias')
    pdf.add_kv('Sinapomorfia', 'Caracteres novedosos compartidos por varios grupos')

    pdf.add_sub_banner('Herramientas de la Evolucion Sistematica', *C_AUTORES_S)
    pdf.add_bullet('Taxonomia')
    pdf.add_bullet('Escuelas evolucionistas (arboles filogeneticos)')
    pdf.add_bullet('Biologia molecular (PCR, ARN, 16S Bacteriano, ADN mitocondrial)')
    pdf.add_bullet('Genetica, Estudio de mutaciones')
    pdf.add_bullet('Geografia, Ecologia, Etiologia (Comportamiento)')

    pdf.add_sub_banner('Clasificacion Taxonomica - DR PEPE COFGE', *C_AUTORES_S)
    pdf.add_table(
        ['Letra', 'Nivel', 'Ejemplo (Homo sapiens)'],
        [
            ['D', 'Dominio / Imperio', 'Eukarya'],
            ['R', 'Reino', 'Animal'],
            ['Pepe', 'Phylum / Division', 'Chordata'],
            ['C', 'Clase', 'Mammalia'],
            ['O', 'Orden', 'Primate'],
            ['F', 'Familia', 'Hominidae'],
            ['G', 'Genero', 'Homo'],
            ['E', 'Especie', 'sapiens'],
        ],
        [60, 150, 290], header_color=C_AUTORES
    )
    pdf.add_paragraph('Clasificacion binomial (G + E): Homo sapiens sapiens. Latin, cursiva, 1er = genero, 2do = especie.', 'Helvetica-Bold', 9)
    pdf.add_spacer()

    pdf.add_banner('PERSONAJES CLAVE DE LA EVOLUCION', *C_AUTORES)

    personajes = [
        ('George-Louis Leclerc DE BUFFON', [
            ('Profesion', 'Naturalista, matematico, biologo, cosmologo frances'),
            ('Libro', 'Historia Natural'),
            ('Teoria', 'Degeneracionista'),
        ]),
        ('James HUTTON', [
            ('Aportacion', 'Padre de la geologia moderna'),
            ('Teoria', 'UNIFORMISTA - La tierra se moldea por procesos naturales'),
        ]),
        ('Charles LYELL', [
            ('Datos', 'Geologo Britanico (1797-1875)'),
            ('Libro', 'Principios de la Geologia'),
        ]),
        ('William SMITH', [
            ('Observacion', 'El suelo se divide en estratos con fosiles caracteristicos'),
        ]),
        ('BARON DE CUVIER', [
            ('Padre de', 'La Paleontologia'),
            ('Teoria', 'CATASTROFISMO'),
            ('Primero en', 'Proponer extincion de dinosaurios; ordenar el reino animal'),
        ]),
        ('Charles BONNET', [
            ('Invencion', 'Invento el termino EVOLUCION'),
            ('Descubrimiento', 'Partenogenesis'),
        ]),
        ('Carlos LINNEO', [
            ('Datos', 'Naturalista sueco (1707-1778)'),
            ('Padre de', 'Taxonomia botanica'),
            ('Libros', 'Systema Naturae; Species Plantarum'),
            ('Creo', 'Clasificacion binomial'),
        ]),
        ('Jean Baptiste LAMARCK', [
            ('Padre de', 'Biologia moderna'),
            ('Terminos', 'Vertebrados, Invertebrados'),
            ('Teorias', 'USO Y DESUSO + HERENCIA de caracteres adquiridos'),
        ]),
        ('August WEISMANN', [
            ('Aportacion', 'Refuto la Teoria del Uso y Desuso de Lamarck'),
        ]),
        ('Gottfried R. TREVIRANUS', [
            ('Aportacion', 'Introdujo el termino BIOLOGIA'),
            ('Libro', 'Biologia y la Filosofia'),
        ]),
        ('Alexander von Humboldt', [
            ('Descripcion', 'Describio la estatua de la Coatlicue'),
            ('Libro', 'Cosmos'),
        ]),
    ]

    for nombre, datos in personajes:
        pdf.add_sub_banner(nombre, *C_AUTORES_S)
        for k, v in datos:
            pdf.add_kv(k, v)


    pdf.add_spacer()
    pdf.add_sub_banner('CHARLES ROBERT DARWIN - Figura Central', *C_AUTORES_S)
    pdf.add_kv('Nacimiento', 'Shrewbury, Inglaterra (1809)')
    pdf.add_kv('Fallecimiento', 'Insuficiencia cardiaca (1882)')
    pdf.add_paragraph('EL VIAJE DEL BEAGLE:', 'Helvetica-Bold', 9)
    pdf.add_kv('Barco', 'HMS Beagle (Her Majesty\'s Ship Beagle)')
    pdf.add_kv('Capitan', 'Robert Fitz Roy')
    pdf.add_kv('Zarpe', 'Plymouth, Davenport [27-Dic-1831]')
    pdf.add_kv('Arribo', 'Falmouth [2-Oct-1836]')
    pdf.add_paragraph('ISLAS GALAPAGOS (pertenecen a Ecuador):', 'Helvetica-Bold', 9)
    pdf.add_bullet('Estudio: pinzones, tortugas gigantes, armadillo, iguanas marinas.')
    pdf.add_bullet('Vio el inicio de la adaptacion.')
    pdf.add_bullet('Terremotos: suelo se levanto -> razon de fosiles marinos en montanas.')
    pdf.add_bullet('Comparo armadillos con Gliptodonte (fosil).')
    pdf.add_paragraph('POSTULADOS DE DARWIN:', 'Helvetica-Bold', 9)
    pdf.add_bullet('Los individuos varian de una poblacion a otra.')
    pdf.add_bullet('Los caracteres se heredan de padres a crias.')
    pdf.add_bullet('Algunos individuos no logran sobrevivir y reproducirse.')
    pdf.add_bullet('La supervivencia y reproduccion NO estan al azar.')
    pdf.add_paragraph('CONCLUSION: Las especies deben adaptarse para sobrevivir. La SELECCION NATURAL es la adaptacion para mantener una especie. UN INDIVIDUO SOLO NO EVOLUCIONA, PERO UNA POBLACION SI.', 'Helvetica-Bold', 9)

    pdf.add_sub_banner('Alfred Russel WALLACE', *C_AUTORES_S)
    pdf.add_kv('Datos', 'Naturalista, explorador britanico (1823-1913)')
    pdf.add_kv('Estudio', 'Amazonas, Archipielago Malayo')
    pdf.add_kv('Conclusion', 'La misma que Darwin - llego de forma independiente')

    pdf.add_paragraph('LIBROS DE DARWIN:', 'Helvetica-Bold', 9)
    pdf.add_bullet('El origen de las especies por medio de la seleccion natural')
    pdf.add_bullet('El origen del hombre y la seleccion en relacion al sexo')
    pdf.add_bullet('El viaje del Beagle')
    pdf.add_bullet('La expresion de las emociones en el hombre y los animales')
    pdf.add_bullet('Insectivorous Plants')

    pdf.add_sub_banner('Karl Ernst VON BAER', *C_AUTORES_S)
    pdf.add_paragraph('Observo embriones de vertebrados: parecidos en primeras etapas. Todos los vertebrados tienen genes para branquias y cola que se INACTIVAN segun especie.', 'Helvetica', 9)

    pdf.add_sub_banner('Ernst Heinrich HAECKEL', *C_AUTORES_S)
    pdf.add_kv('Datos', 'Naturalista aleman (1834-1919). Monista.')
    pdf.add_kv('Terminos', 'Phylum, Ecologia, Ontogenia, Filogenia, Phitecantropus')
    pdf.add_kv('Libro', 'Morfologia General de los Organismos')
    pdf.add_kv('Creo', 'Taxon Moneres para clasificacion de bacterias')
    pdf.add_spacer()

    pdf.add_banner('ANALOGIAS, HOMOLOGIAS Y ESTRUCTURAS VESTIGIALES', *C_AUTORES)
    pdf.add_table(
        ['Concepto', 'Anatomia', 'Funcion', 'Significado evolutivo'],
        [
            ['ANALOGIA fenotipica', 'Diferente', 'Similar', 'Convergencia evolutiva'],
            ['HOMOLOGIA fenotipica', 'Misma', 'Diferente', 'Comparten ancestro comun'],
        ],
        [120, 80, 80, 220], header_color=C_AUTORES
    )
    pdf.add_paragraph('ESTRUCTURAS VESTIGIALES:', 'Helvetica-Bold', 9)
    pdf.add_kv('Serpientes', 'Espolones (restos de patas)')
    pdf.add_kv('Murcielagos hematofagos', 'Molares (no eran hematofagos)')
    pdf.add_kv('Ballenas', 'Cadera (tenian patas traseras)')
    pdf.add_spacer()


    pdf.add_banner('ESCUELAS EVOLUCIONISTAS', *C_AUTORES)
    pdf.add_table(
        ['Escuela', 'Grupos que acepta', 'Caracteristica'],
        [
            ['CLADISTAS', 'Solo Monofileticos', 'Clasificacion estricta por ancestro comun'],
            ['EVOLUCIONISTAS', 'Mono + Parafileticos', 'Acepta grupos parafilos'],
            ['FENETISTAS', 'Mono + Para + Polifilet.', 'Clasificacion por similitud fenotipica'],
        ],
        [120, 150, 230], header_color=C_AUTORES
    )
    pdf.add_table(
        ['Termino', 'Definicion', 'Natural'],
        [
            ['MONOFILETICOS', 'TODOS los descendientes de un ancestro comun', 'Si'],
            ['PARAFILETICOS', 'Ancestro y UNA PARTE de su descendencia', 'Con reservas'],
            ['POLIFILET.', 'Ramas dispersas; NO incluye antepasado comun reciente', 'No'],
        ],
        [110, 290, 100], header_color=C_AUTORES
    )
    pdf.add_paragraph('Ejemplos hibridos (polfiletico): Cebrasno, Ligre, Burdegano, Mula.', 'Helvetica', 9)
    pdf.add_spacer()

    pdf.add_banner('ESPECIACION', *C_AUTORES)
    pdf.add_paragraph('Definicion: Hecho de que aparezcan nuevas especies.', 'Helvetica-Bold', 9)
    pdf.add_table(
        ['Tipo', 'Mecanismo', 'Descripcion'],
        [
            ['ALOPATRICA', 'Aislamiento geografico', 'Barrera fisica separa poblacion -> cambios independientes'],
            ['PARAPATRICA', 'Condiciones ambientales', 'Especies por condiciones distintas, misma area (NO mezclados)'],
            ['SIMPATRICA', 'Nichos distintos', 'Especies por nichos ecologicos diferentes (MEZCLADOS)'],
        ],
        [100, 130, 270], header_color=C_AUTORES
    )

    pdf.add_sub_banner('Tipos de Aislamiento Reproductivo', *C_AUTORES_S)
    pdf.add_kv('ECOLOGICO', 'Distintas poblaciones se adaptan a distintos habitats')
    pdf.add_kv('ETOLOGICO', 'Se crean/modifican senales de atraccion o apaciguamiento')
    pdf.add_kv('SEXUAL', 'Variacion de organos o de los gametos')
    pdf.add_kv('GENETICO', 'Cambios cromosomicos que producen esterilidad de hibridos')

    pdf.new_page()


    # ============================================================
    # SECCION 4: EXAMEN INTEGRADOR
    # ============================================================
    pdf.add_cover('EXAMEN INTEGRADOR', [
        'Flores & Plantae - Reino Fungi - Evolucion y Autores',
        'Instrucciones: Lee cada pregunta y responde.'
    ], *C_DARK)
    pdf.add_spacer(12)

    pdf.add_paragraph('INSTRUCCIONES: Lee cuidadosamente cada pregunta. Responde con base en lo estudiado.', 'Helvetica-Bold', 10)
    pdf.add_hr()
    pdf.add_spacer()

    pdf.add_banner('BLOQUE 1: LAS FLORES Y PLANTAS VASCULARES', *C_FLORES)
    q_flores = [
        '1. Que diferencia a una flor perfecta de una imperfecta?',
        '2. Que es el gametofito masculino en estado inmaduro?',
        '3. Nombra 2 plantas dioicas y 2 plantas monoicas.',
        '4. De que estructura se forma el fruto? y el endosperma?',
        '5. Que es la giberelina y cual es su funcion en la semilla?',
        '6. Por que la raiz no tiene cloroplastos pero si leucoplastos?',
        '7. Explica la funcion de la caliptra.',
        '8. Que diferencia hay entre el xilema y el floema?',
        '9. Que es la dominancia apical y que hormona la regula?',
        '10. Que es el geotropismo? Que estructuras lo permiten?',
        '11. Menciona 2 tipos de frutos carnosos con un ejemplo cada uno.',
        '12. Cual es la diferencia entre un tuberculo y un bulbo?',
        '13. Que es la fotoperiocidad en plantas?',
        '14. Que sustancias quimicas usan las plantas para defenderse?',
        '15. Describe el mecanismo de captura de la Drosera.',
    ]
    for q in q_flores:
        pdf.add_paragraph(q, 'Helvetica', 9)
        pdf.add_spacer(10)
        pdf.add_hr()

    pdf.add_spacer()
    pdf.add_banner('BLOQUE 2: REINO FUNGI Y PLANTAE', *C_FUNGI)
    q_fungi = [
        '16. De que esta compuesta la pared celular de los hongos?',
        '17. Cual es la diferencia entre saprofito y parasito?',
        '18. Que es la osmotrofia?',
        '19. Por que los Quitridiomicetos son unicos entre los hongos?',
        '20. Menciona el hongo mas grande del mundo y su grupo.',
        '21. Que son las basidiosporas y en que grupo se forman?',
        '22. Cual es el proceso para formar una bebida alcoholica con levaduras?',
        '23. Que es el ergotismo y de que hongo proviene?',
        '24. Que diferencia hay entre endo y ectomicorrizas?',
        '25. Menciona 3 beneficios de las micorrizas.',
        '26. Que organismos forman un liquen?',
        '27. Por que los liquenes son importantes ecologicamente?',
        '28. Explica la diferencia entre gametofito y esporofito.',
        '29. Que son las Briofitas? Menciona sus 3 clases.',
        '30. Cual es la diferencia entre Gimnospermas y Angiospermas?',
    ]
    for q in q_fungi:
        pdf.add_paragraph(q, 'Helvetica', 9)
        pdf.add_spacer(10)
        pdf.add_hr()

    pdf.add_spacer()
    pdf.add_banner('BLOQUE 3: EVOLUCION, AUTORES Y TEORIAS', *C_AUTORES)
    q_autores = [
        '31. Cual es la frase celebre de Dobzhansky?',
        '32. Menciona los 3 hechos naturales de la Sintesis Evolutiva Moderna.',
        '33. Cuales son las 4 condiciones del Equilibrio de Hardy-Weinberg?',
        '34. Quien propuso los dominios Eukarya, Procaria y Archea?',
        '35. Define: taxon, clado y sinapomorfia.',
        '36. Que significa la mnemotecnia "DR Pepe COFGE"?',
        '37. Quien es el padre de la taxonomia botanica? Que sistema creo?',
        '38. Cual es la diferencia entre la teoria de Lamarck y la de Darwin?',
        '39. Que observo Darwin en las Islas Galapagos?',
        '40. A que pais pertenecen las Islas Galapagos?',
        '41. Cual fue el barco del viaje de Darwin y quien era el capitan?',
        '42. Que refuto August Weismann?',
        '43. Explica la diferencia entre analogia y homologia.',
        '44. Menciona 3 estructuras vestigiales con el animal que las posee.',
        '45. Cual es la diferencia entre especiacion alopatrica y simpatrica?',
        '46. Que es el aislamiento genetico en especiacion?',
        '47. Cual es la diferencia entre un grupo monofiletico y polfiletico?',
        '48. Menciona 2 libros escritos por Darwin.',
        '49. Que es la Abadia de Westminster? Menciona 3 personas enterradas ahi.',
        '50. Quien introdujo el termino "biologia" y en que libro?',
    ]
    for q in q_autores:
        pdf.add_paragraph(q, 'Helvetica', 9)
        pdf.add_spacer(10)
        pdf.add_hr()

    pdf.add_spacer(12)
    pdf.add_paragraph('Las preguntas corresponden al contenido de los apuntes del documento original. Buena suerte!', 'Helvetica', 8)

    # === NOTA FINAL ===
    pdf.new_page()
    pdf.add_banner('NOTA SOBRE EL CONTENIDO', 0.26, 0.26, 0.26)
    pdf.add_paragraph('Todo el texto corresponde fielmente al contenido de los PDFs de clase proporcionados.', 'Helvetica', 9)
    pdf.add_paragraph('Fuentes: FLORES.pdf | REINO_FUNGI_.pdf | Autores_y_teorias_.pdf', 'Helvetica-Bold', 9)

    # === SAVE ===
    output = '/projects/sandbox/Apuntes_Biologia_Completo.pdf'
    pdf.save(output)
    print(f"PDF generado exitosamente: {output}")
    return output


if __name__ == '__main__':
    build_document()
