import math
import sqlite3
import struct

from bs4 import BeautifulSoup
import csvs_to_sqlite
import pandas as pd
import requests


UF = {
    'AC': 'Acre',
    'AL': 'Alagoas',
    'AP': 'Amapá',
    'AM': 'Amazonas',
    'BA': 'Bahia',
    'CE': 'Ceará',
    'DF': 'Distrito Federal',
    'ES': 'Espírito Santo',
    'GO': 'Goiás',
    'MA': 'Maranhão',
    'MT': 'Mato Grosso',
    'MS': 'Mato Grosso do Sul',
    'MG': 'Minas Gerais',
    'PA': 'Pará',
    'PB': 'Paraíba',
    'PR': 'Paraná',
    'PE': 'Pernambuco',
    'PI': 'Piauí',
    'RJ': 'Rio de Janeiro',
    'RN': 'Rio Grande do Norte',
    'RS': 'Rio Grande do Sul',
    'RO': 'Rondônia',
    'RR': 'Roraima',
    'SC': 'Santa Catarina',
    'SP': 'São Paulo',
    'SE': 'Sergipe',
    'TO': 'Tocantins'}


def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])


class OpenDataCNPJ():
    url_rfb = ('http://idg.receita.fazenda.gov.br/orientacao/tributaria/'
               'cadastros/cadastro-nacional-de-pessoas-juridicas-cnpj/'
               'dados-abertos-do-cnpj')

    INFO_SOCIO = '02'
    INFO_EMPRESA = '01'

    def __init__(self):
        self.HTML = self.get_page_source()

    def get_page_source(self):
        source = requests.get(self.url_rfb).content
        return source

    def get_data_url(self):
        soup = BeautifulSoup(self.HTML, 'lxml')
        tabela_links = soup.findAll('table')[0]
        links = tabela_links.findAll('a')
        return {i['href'][-2:]: i['href'] for i in links}

    def get_link_dados_uf(self, nome_uf):
        return self.get_data_url()[nome_uf]

    def get_file_size(self, url):
        headers = {'Range': 'bytes=0-1'}
        info = requests.get(url, headers=headers).headers
        file_size = int(info['Content-Range'].split('/')[1])
        return convert_size(file_size)

    def info_type(self, text):
        if text.startswith(self.INFO_EMPRESA):
            info_type = self.INFO_EMPRESA
        elif text.startswith(self.INFO_SOCIO):
            info_type = self.INFO_SOCIO
        else:
            raise ValueError(f'Dados inválidos: {text}')
        return info_type

    def parse_info(self, text, field_widths=()):
        fmtstring = ' '.join('{}{}'.format(abs(fw), 'x' if fw < 0 else 's')
                             for fw in field_widths)
        fieldstruct = struct.Struct(fmtstring)
        parse = fieldstruct.unpack_from
        fields = [i.decode().strip() for i in parse(text.encode())]
        return fields

    def parse_cnpj_data(self, data):
        info_empresas = []
        info_shareholders = []
        empresa_field_widths = (2, 14, 150)
        shareholders_field_widths = (2, 14, 1, 14, 2, 150)

        for n, line in enumerate(data):
            if self.info_type(line) == self.INFO_EMPRESA:
                data = self.parse_info(line, field_widths=empresa_field_widths)
                info_empresas.append(data)

            elif self.info_type(line) == self.INFO_SOCIO:
                data = self.parse_info(line, field_widths=shareholders_field_widths)
                ''' Corrige string vazia retornada no lugar de zero no campo
                cpf/cnpj do sócio '''
                if data[3] == '':
                    data[3] = 0
                info_shareholders.append(data)

        cols_empresa = ['tipo', 'cnpj', 'nome_empresarial']
        cols_shareholders = ['tipo', 'cnpj', 'indicador_cpf_cnpj', 'cpf_cnpj',
                         'qualificacao_socio', 'nome_socio']

        dados_empresas = pd.DataFrame(columns=cols_empresa, data=info_empresas)
        del dados_empresas['tipo']

        shareholders = pd.DataFrame(columns=cols_shareholders, data=info_shareholders)
        # Insere a descrição do campo indicador cpf/cnpj na tabela de sócios.
        del shareholders['tipo']
        desc_indicador_cpf_cnpj = {'1': 'Pessoa Jurídica',
                                   '2': 'Pessoa Física',
                                   '3': 'Nome Exterior'}

        for desc in desc_indicador_cpf_cnpj:
            lines = shareholders['indicador_cpf_cnpj'] == desc
            shareholders.loc[lines, 'ds_indicador_cpf_cnpj'] = desc_indicador_cpf_cnpj[desc]
        return dados_empresas, shareholders

    def download_data(self, uf):
        data_urls = self.get_data_url()
        url = data_urls[uf.upper()]
        file_size = self.get_file_size(url)
        print(f'{uf}: Downloading data ({file_size}).')
        data = requests.get(url).text.splitlines()
        return data

    def get_data(self, UF):
        data = self.download_data(UF)
        companies, shareholders = self.parse_cnpj_data(data)
        companies.insert(0, 'UF', UF)
        shareholders.insert(0, 'UF', UF)
        return companies, shareholders


if __name__ == '__main__':
    companies = pd.DataFrame()
    shareholders = pd.DataFrame()

    openData = OpenDataCNPJ()
    for sigla_UF in UF:
        empresas_uf, socios_uf = openData.get_data(sigla_UF)
        companies = companies.append(empresas_uf)
        shareholders = shareholders.append(socios_uf)

    companies_count = len(companies)
    shareholders_count = len(shareholders)
    print(f'Encontradas {format(companies_count, ",.2f")} empresas.')
    print(f'Encontrados {format(shareholders_count, ",.2f")} sócios.')

    print('Exporting data to csv.')
    #companies.to_csv('empresas_brasil.csv', sep=';', index=False)
    #shareholders.to_csv('socios_brasil.csv', sep=';', index=False)

    print('Exporting data to Sqlite database.')
    database = 'open_cnpj.db'
    con = sqlite3.connect(database)
    companies.to_sql('empresas', con, index=False, if_exists='replace')
    shareholders.to_sql('socios', con, index=False, if_exists='replace')
