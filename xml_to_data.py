import xml.etree.cElementTree as ET
from urllib.request import urlopen
from bs4 import BeautifulSoup
import jinja2
import pdfkit
import requests
from PyPDF2 import PdfFileMerger
import shutil
import os
from PIL import Image
import csv

local_path = os.environ.get("LOCAL_PATH")

max_num_lines_xml_request = 128

class XmlToBookData:
    def __init__(self, isbn_list, login, password):
        self.book_dictionary = {}
        self.error_dictionary = {}
        self.login = login
        self.password = password
        self.template_path = "source/"
        self.template_name = "template.html"
        self.css_file = local_path + "source/style.css"
        self.image_path = local_path + "source/book_covers/"
        self.logo = local_path + "source/logo-panoplia-medium.jpg"

        count = 1
        short_isbn_list = []
        for isbn in isbn_list:
            short_isbn_list.append(isbn)
            if count % max_num_lines_xml_request == 0:
                url = self.create_url_from_list(short_isbn_list)
                self.read_xml(url)
                short_isbn_list = []
            count += 1
        if count < 128:
            url = self.create_url_from_list(short_isbn_list)
            self.read_xml(url)

    def file_to_list(self, input_file):
        # Open file and returns ISBNs on a list
        with open(input_file, 'r', encoding="UTF-8") as file:
            isbn_list = file.read().splitlines()
        return isbn_list

    def create_url_from_list(self, isbn_list):
        # Formats the url in the correct format
        isbn_string = "|".join(isbn_list)
        url = url_request = f'https://www.dilve.es/dilve/dilve/getRecordsX.do?user={self.login}&password={self.password}&identifier={isbn_string}'
        return url

    def read_xml(self, xml_input_url):
        # Fetch data from DILVE and returns a dictionary with the correct information
        document = ET.parse(urlopen(xml_input_url))
        root = document.getroot()
        for book in root.iter("{http://www.editeur.org/onix/2.1/reference}Product"):
            isbn = ""
            title = ""
            author = ""
            editor = ""
            year = ""
            number_pages = ""
            width = ""
            height = ""
            unit_measure = ""
            price = ""
            currency = ""
            description = ""
            image_media = ""
            image_url = ""
            image_code = ""
            isbn = book.findtext("{http://www.editeur.org/onix/2.1/reference}RecordReference")
            title = book.findtext("{http://www.editeur.org/onix/2.1/reference}Title/{http://www.editeur.org/onix/2.1/reference}TitleText")
            if isinstance(book.findtext("{http://www.editeur.org/onix/2.1/reference}Title/{http://www.editeur.org/onix/2.1/reference}Subtitle"), str):
                title = title + " | " + book.findtext("{http://www.editeur.org/onix/2.1/reference}Title/{http://www.editeur.org/onix/2.1/reference}Subtitle")
            # A01 es el autor otros pueden ser los traductores
            for contributor in book.findall("{http://www.editeur.org/onix/2.1/reference}Contributor"):
                if contributor.findtext("{http://www.editeur.org/onix/2.1/reference}ContributorRole") == "A01":
                    author = contributor.findtext("{http://www.editeur.org/onix/2.1/reference}PersonNameInverted")

            # Texto 01 es el de la contratapa
            description = ""
            for text in book.findall("{http://www.editeur.org/onix/2.1/reference}OtherText"):
                if text.findtext("{http://www.editeur.org/onix/2.1/reference}TextTypeCode") == "01":
                    if text.find("{http://www.editeur.org/onix/2.1/reference}Text").text.strip() not in (None, ""):
                        description = text.findtext("{http://www.editeur.org/onix/2.1/reference}Text")
                    else:
                        description = ""
                        for child in text.find("{http://www.editeur.org/onix/2.1/reference}Text"):
                            description += ET.tostring(child, encoding="unicode")
            soup = BeautifulSoup(description, features="html.parser")
            description = soup.get_text()
            editor = book.findtext("{http://www.editeur.org/onix/2.1/reference}Imprint/{http://www.editeur.org/onix/2.1/reference}ImprintName")
            year = book.findtext("{http://www.editeur.org/onix/2.1/reference}YearFirstPublished")
            for measure in book.findall("{http://www.editeur.org/onix/2.1/reference}Measure"):
                if measure.findtext("{http://www.editeur.org/onix/2.1/reference}MeasureTypeCode") == "01":
                    width = measure.findtext("{http://www.editeur.org/onix/2.1/reference}Measurement")
                elif measure.findtext("{http://www.editeur.org/onix/2.1/reference}MeasureTypeCode") == "02":
                    height = measure.findtext("{http://www.editeur.org/onix/2.1/reference}Measurement")

            unit_measure = book.findtext("{http://www.editeur.org/onix/2.1/reference}Measure/{http://www.editeur.org/onix/2.1/reference}MeasureUnitCode")
            price = book.findtext("{http://www.editeur.org/onix/2.1/reference}SupplyDetail/{http://www.editeur.org/onix/2.1/reference}Price/{http://www.editeur.org/onix/2.1/reference}PriceAmount")
            currency = book.findtext("{http://www.editeur.org/onix/2.1/reference}SupplyDetail/{http://www.editeur.org/onix/2.1/reference}Price/{http://www.editeur.org/onix/2.1/reference}CurrencyCode")
            number_pages = book.findtext("{http://www.editeur.org/onix/2.1/reference}NumberOfPages")
            image_code = book.findtext("{http://www.editeur.org/onix/2.1/reference}MediaFile/{http://www.editeur.org/onix/2.1/reference}MediaFileLinkTypeCode")
            image_media = book.findtext("{http://www.editeur.org/onix/2.1/reference}MediaFile/{http://www.editeur.org/onix/2.1/reference}MediaFileLink")
            if image_code == "01":
                image_url = image_media
            elif image_code == "06":
                image_url = f"https://www.dilve.es/dilve/dilve/getResourceX.do?user={self.login}&password={self.password}&identifier={isbn}&resource={image_media}"
            self.book_dictionary[isbn] = {
                "title": title,
                "author": author,
                "editor": editor,
                "year": year,
                "number_pages": number_pages,
                "width": width,
                "height": height,
                "unit_measure": unit_measure,
                "price": price,
                "currency": currency,
                "description": description,
                "image_url": image_url
            }
        for error in root.iter("{http://www.dilve.es/dilve/api/xsd/getRecordsXResponse}error"):
            self.error_dictionary[error.findtext("{http://www.dilve.es/dilve/api/xsd/getRecordsXResponse}identifier")] = error.findtext("{http://www.dilve.es/dilve/api/xsd/getRecordsXResponse}text")

    def download_covers(self):
        for book, book_data in self.book_dictionary.items():
            if book_data["image_url"]:
                list_url = book_data["image_url"].split(".")
                extension = list_url[-1]
                image_file = f"source/book_covers/{book}.{extension}"
                with open(image_file, 'wb') as f:
                    f.write(requests.get(book_data["image_url"]).content)
                self.resize_image(image_file)
            else:
                shutil.copyfile("source/blank_book.jpg", f"source/book_covers/{book}.jpg")

    def resize_image(self, image_file):
        base_width = 290
        try:
            img = Image.open(image_file)
        except:
            print(f"Cannot open image {image_file}")
        else:
            width_percent = (base_width / float(img.size[0]))
            height_size = int((float(img.size[1]) * float(width_percent)))
            img = img.resize((base_width, height_size), Image.ANTIALIAS)
            img.save(image_file)

    def create_pdf(self,):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_path))
        template = env.get_template(self.template_name)
        options = {
            "page-size": "Letter",
            "margin-top": "0.05in",
            "margin-bottom": "0.05in",
            "margin-left": "0.05in",
            "margin-right": "0.05in",
            "encoding": "UTF-8"

        }

        # config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
        config = pdfkit.configuration(wkhtmltopdf="source/bin/wkhtmltopdf")
        input_data = {}
        pdf_list = []
        for isbn, book_data in self.book_dictionary.items():
            list_url = book_data["image_url"].split(".")
            extension = list_url[-1]
            cover = self.image_path+isbn+"."+extension
            input_data = {
                "logo": self.logo,
                "title": book_data["title"],
                "author": book_data["author"],
                "isbn": isbn,
                "cover": cover,
                "editor": book_data["editor"],
                "year": book_data["year"],
                "number_pages": book_data["number_pages"],
                "width": book_data["width"],
                "height": book_data["height"],
                "unit_measure": book_data["unit_measure"],
                "price": book_data["price"],
                "currency": book_data["currency"],
                "description": book_data["description"],
            }

            html = template.render(input_data)
            output_pdf_file = f"{local_path}source/output/{isbn}.pdf"
            pdf_list.append(output_pdf_file)
            print(output_pdf_file)
            pdfkit.from_string(html, output_pdf_file, css=self.css_file, options=options, configuration=config)
            os.remove(cover)

        # Merge PDF;
        merger = PdfFileMerger()
        for pdf in pdf_list:
            merger.append(pdf)
            os.remove(pdf)
        merger.write("static/files/recomendacion_panoplia.pdf")
        merger.close()

    def create_csv(self):
        header = ["ISBN", "Título", "Autor", "Editor", "Precio público", "Cantidad"]
        data = []
        for isbn, book_data in self.book_dictionary.items():
            data.append([
                isbn,
                book_data["title"],
                book_data["author"],
                book_data["editor"],
                book_data["price"]
                ]
            )
        with open("static/files/pedido_panoplia.csv", "w", encoding="UTF8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)


