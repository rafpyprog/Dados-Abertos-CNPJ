import os
from tempfile import TemporaryDirectory

from captchasolver.captchasolver import solve
import requests
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


rfb = 'http://www.receita.fazenda.gov.br/PessoaJuridica/CNPJ/cnpjreva/Cnpjreva_Solicitacao.asp'
audio_url = 'http://www.receita.fazenda.gov.br/PessoaJuridica/CNPJ/cnpjreva/captcha/gerarSom.asp'

chrome = Chrome()
chrome.get(rfb)

chrome.switch_to_frame('main')
chrome.find_element_by_name('captchaSonoro').click()
WebDriverWait(chrome, 5).until(EC.presence_of_element_located((By.ID, 'imgCaptcha')))

cookies = chrome.get_cookies()
cookie_name = cookies[0]["name"]
cookie_value = cookies[0]["value"]
session_cookie = {cookie_name: cookie_value}
print(session_cookie)

referer = 'http://www.receita.fazenda.gov.br/PessoaJuridica/CNPJ/cnpjreva/Cnpjreva_solicitacao3.asp'

headers={'Referer': referer}
r = requests.get(audio_url, headers=headers, cookies=session_cookie)
wav = r.content
with TemporaryDirectory() as tmpdir:
    audiofile = os.path.join(tmpdir, 'tmpaudio.wav')
    with open(audiofile, 'wb') as f:
        f.write(wav)
    solucao_captcha = solve(audiofile)
