from tkinter import *
from tkinter import ttk
from datetime import datetime
from tkcalendar import DateEntry
import requests
import json
from PIL import ImageTk, Image
from urllib.request import urlopen
from zipfile import ZipFile
from io import BytesIO
import rasterio

r = re.compile('.*/IMG_DATA/.*_B\d\d.jp2')

with open('map.json') as arq_json:
    obj = json.load(arq_json)
    footprint = obj['geometry']
    token = obj['token']

year, month, day = str(datetime.date(datetime.now())).split('-')
year, month, day = int(year), int(month), int(day)

class GUI(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.geometry("1280x960")
        self.master.title('Upscaling de Imagens da Sentinel')
        self.pack()
        self.create_GUI_elements()

    def create_GUI_elements(self):
        self.top = Frame(self, relief=RAISED, borderwidth=1)
        self.top.pack(pady=5, padx=5, fill=BOTH)

        self.pesquisa = Frame(self.top)
        self.pesquisa.pack(pady=5, padx=5, anchor=CENTER)

        self.meio = Frame(self, relief=RAISED, borderwidth=1)
        self.meio.pack(pady=5, padx=5, fill=BOTH)
        self.bot = Frame(self, relief=RAISED, borderwidth=1)
        self.bot.pack(side="bottom", pady=5, padx=5, fill=BOTH)

        self.data_inicial = DateEntry(self.pesquisa, width=12, year=year, month=month, day=day-1, background='darkblue', foreground='gray', borderwidth=2)
        self.data_inicial.pack(side=LEFT, pady=5)
        self.data_final = DateEntry(self.pesquisa, width=12, year=year, month=month, day=day, background='darkblue', foreground='gray', borderwidth=2)
        self.data_final.pack(side=LEFT, padx=5)

        self.lista = ttk.Treeview(self.meio, columns=('Periodo', f'% de Nuvens', 'Tamanho'))
        self.lista.column('#0', width=400, anchor=CENTER)
        self.lista.heading('#0', text='Titulo')
        self.lista.column('#1', width=180, anchor=CENTER)
        self.lista.heading('#1', text='Periodo')
        self.lista.column('#2', width=100, anchor=CENTER)
        self.lista.heading('#2', text=f'% de Nuvens')
        self.lista.column('#3', width=80, anchor=CENTER)
        self.lista.heading('#3', text='Tamanho')

        self.lista.pack(pady=10, padx=10)

        img = ImageTk.PhotoImage(Image.open('BLANK.png').resize((500,500), Image.ANTIALIAS))
        self.imagem = Label(self.meio, image = img, width=500, height=500)
        self.imagem.image = img
        self.imagem.pack(pady= 10, padx=10)
        self.iid=0

        self.search = Button(self.pesquisa, text="Busca", command=self.search_image).pack(side="left", padx=5)

        self.texto = StringVar()
        self.texto.set("Download Imagem: NONE")

        self.down = Button(self.bot, textvariable=self.texto, fg="black", command=self.download)
        self.down.pack(pady=10)

        self.quit = Button(self.bot, text="SAIR", fg="black", command=self.master.destroy)
        self.quit.pack(side="bottom", pady=10)

    def download(self):

        url = self.down_alvo + token

        with urlopen(url) as zipresp:
            with ZipFile(BytesIO(zipresp.read())) as zfile:
                lines_to_log = [line for line in zfile.namelist() if r.match(line)]
                for files in lines_to_log:
                    zfile.extract(files, './temp/')
        
        arq = lines_to_log[0].split(".")[0] + ".tiff"

        b = rasterio.open('./temp/' + lines_to_log[1])
        g = rasterio.open('./temp/' + lines_to_log[2])
        red = rasterio.open('./temp/' + lines_to_log[3])

        with rasterio.open(arq, 'w', driver='Gtiff', width=b.width, height=b.height, count=3, crs=b.crs, 
            transform=b.transform, dtype=b.dtypes[0]) as rgb:
            rgb.write(b.read(1), 3)
            rgb.write(g.read(1), 2)
            rgb.write(red.read(1), 1)
            rgb.close()

    def show_imagem(self, Event):

        url = self.lista_imagens[int(Event.widget.selection()[0])]
        raw_img = Image.open(requests.get(url, stream=True).raw).resize((500,500), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(raw_img)
        self.imagem.configure(image=img)
        self.imagem.image = img
        self.texto.set('Download Imagem: ' + self.lista.item(int(Event.widget.selection()[0]))['text'])
        self.down_alvo = self.lista_down[int(Event.widget.selection()[0])]

    def search_image(self):

        self.iid = 0

        self.lista_imagens = []
        self.lista_down = []
        self.down_alvo = ''

        data_ini = str(self.data_inicial.get_date()) + "T00%3A00%3A00Z"
        data_fim = str(self.data_final.get_date()) + "T23%3A59%3A59Z"
        
        resp = requests.get(f'https://finder.creodias.eu/resto/api/collections/Sentinel2/search.json?maxRecords=10&publishedAfter={data_ini}&publishedBefore={data_fim}&processingLevel=LEVEL1C&sortParam=startDate&sortOrder=descending&status=all&geometry={footprint}&dataset=ESA-DATASET')

        dados = resp.json()

        for item in dados['features']:

            self.lista.insert('', END, iid=self.iid, text= str(item['properties']['title'][:-5]),
                values=(item['properties']['startDate'], item['properties']['cloudCover'], item['properties']['services']['download']['size']))
            self.lista_imagens.append(item['properties']['thumbnail'])
            self.lista_down.append(item['properties']['services']['download']['url'])
            self.iid = self.iid + 1

        self.lista.bind('<<TreeviewSelect>>', self.show_imagem)


main_window = Tk()

janela = GUI(master=main_window)
janela.mainloop()