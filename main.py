from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from datetime import date
from typing import Optional
from dotenv import load_dotenv
import pyodbc
import json
import os
import requests

load_dotenv()

API_KEY = os.getenv("API_KEY")
DB_DRIVER = os.getenv("DB_DRIVER")
DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

app = FastAPI()

def get_conexao():
    return pyodbc.connect(
        f"DRIVER={DB_DRIVER};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

def verificar_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente")

def registrar_log(endpoint, metodo, payload, status, mensagem_erro=None, id_gerado=None):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("""
        INSERT INTO LogIntegracao (Endpoint, MetodoHttp, PayloadRecebido, Status, MensagemErro, IdGerado)
        VALUES (?, ?, ?, ?, ?, ?)
    """, endpoint, metodo, payload, status, mensagem_erro, id_gerado)
    conexao.commit()
    conexao.close()

def tratar_data_publicacao(data_str):
    if not data_str:
        return None
    partes = data_str.split("-")
    if len(partes) == 1:
        return f"{partes[0]}-01-01"
    elif len(partes) == 2:
        return f"{partes[0]}-{partes[1]}-01"
    else:
        return data_str

def buscar_ou_criar_editora(nome_editora, cursor, conexao):
    if not nome_editora:
        nome_editora = "Editora não informada"

    cursor.execute("SELECT IdEditora FROM Editora WHERE NomeEditora = ?", nome_editora)
    linha = cursor.fetchone()

    if linha:
        return linha.IdEditora

    cursor.execute("""
        INSERT INTO Editora (NomeEditora)
        OUTPUT INSERTED.IdEditora
        VALUES (?)
    """, nome_editora)
    novo_id = cursor.fetchone()[0]
    conexao.commit()
    return novo_id

def buscar_ou_criar_assunto(nome_assunto, cursor, conexao):
    if not nome_assunto:
        nome_assunto = "Assunto não informado"

    cursor.execute("SELECT IdAssunto FROM Assunto WHERE NomeAssunto = ?", nome_assunto)
    linha = cursor.fetchone()

    if linha:
        return linha.IdAssunto

    cursor.execute("""
        INSERT INTO Assunto (NomeAssunto)
        OUTPUT INSERTED.IdAssunto
        VALUES (?)
    """, nome_assunto)
    novo_id = cursor.fetchone()[0]
    conexao.commit()
    return novo_id

class LivroEntrada(BaseModel):
    NomeLivro: str
    ISBN13: str
    DataPub: Optional[date] = None
    PrecoLivro: float
    NumeroPaginas: int
    IdEditora: int
    IdAssunto: int
    Edicao: Optional[int] = None

class DeleteLoteEntrada(BaseModel):
    ids: list[int]

@app.post("/livros", dependencies=[Depends(verificar_api_key)])
def criar_livro(livro: LivroEntrada):
    payload_json = livro.model_dump_json()
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT IdLivro FROM Livro WHERE ISBN13 = ?", livro.ISBN13)
        livro_existente = cursor.fetchone()

        if livro_existente:
            registrar_log("/livros", "POST", payload_json, "ERRO", mensagem_erro=f"ISBN já cadastrado (IdLivro: {livro_existente.IdLivro})")
            raise HTTPException(status_code=409, detail=f"ISBN já cadastrado para o livro de IdLivro {livro_existente.IdLivro}")

        cursor.execute("""
            INSERT INTO Livro (NomeLivro, ISBN13, DataPub, PrecoLivro, NumeroPaginas, IdEditora, IdAssunto, Edicao)
            OUTPUT INSERTED.IdLivro
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, livro.NomeLivro, livro.ISBN13, livro.DataPub, livro.PrecoLivro,
             livro.NumeroPaginas, livro.IdEditora, livro.IdAssunto, livro.Edicao)

        novo_id = cursor.fetchone()[0]
        conexao.commit()

        registrar_log("/livros", "POST", payload_json, "SUCESSO", id_gerado=novo_id)

        return {"mensagem": "Livro cadastrado com sucesso!", "IdLivro": novo_id}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log("/livros", "POST", payload_json, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()

@app.get("/livros")
def listar_livros(page: int = 1, limit: int = 10):
    conexao = get_conexao()
    cursor = conexao.cursor()

    cursor.execute("SELECT COUNT(*) FROM Livro")
    total_livros = cursor.fetchone()[0]
    total_paginas = (total_livros + limit - 1) // limit if total_livros > 0 else 0

    pular = (page - 1) * limit
    cursor.execute("""
        SELECT IdLivro, NomeLivro, ISBN13, PrecoLivro
        FROM Livro
        ORDER BY IdLivro
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """, pular, limit)

    colunas = [coluna[0] for coluna in cursor.description]
    livros = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()

    return {
        "total_livros": total_livros,
        "pagina_atual": page,
        "total_paginas": total_paginas,
        "livros": livros
    }

@app.put("/livros/{id_livro}", dependencies=[Depends(verificar_api_key)])
def atualizar_livro(id_livro: int, livro: LivroEntrada):
    payload_json = livro.model_dump_json()
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("""
            UPDATE Livro
            SET NomeLivro = ?, ISBN13 = ?, DataPub = ?, PrecoLivro = ?,
                NumeroPaginas = ?, IdEditora = ?, IdAssunto = ?, Edicao = ?
            WHERE IdLivro = ?
        """, livro.NomeLivro, livro.ISBN13, livro.DataPub, livro.PrecoLivro,
             livro.NumeroPaginas, livro.IdEditora, livro.IdAssunto, livro.Edicao, id_livro)

        if cursor.rowcount == 0:
            registrar_log(f"/livros/{id_livro}", "PUT", payload_json, "ERRO", mensagem_erro="Livro não encontrado")
            raise HTTPException(status_code=404, detail="Livro não encontrado")

        conexao.commit()
        registrar_log(f"/livros/{id_livro}", "PUT", payload_json, "SUCESSO", id_gerado=id_livro)
        return {"mensagem": "Livro atualizado com sucesso!", "IdLivro": id_livro}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/{id_livro}", "PUT", payload_json, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()

@app.delete("/livros/{id_livro}", dependencies=[Depends(verificar_api_key)])
def deletar_livro(id_livro: int):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT * FROM Livro WHERE IdLivro = ?", id_livro)
        linha = cursor.fetchone()

        if linha is None:
            registrar_log(f"/livros/{id_livro}", "DELETE", None, "ERRO", mensagem_erro="Livro não encontrado")
            raise HTTPException(status_code=404, detail="Livro não encontrado")

        colunas = [coluna[0] for coluna in cursor.description]
        registro_deletado = dict(zip(colunas, linha))
        registro_deletado_json = json.dumps(registro_deletado, default=str)

        cursor.execute("DELETE FROM Livro WHERE IdLivro = ?", id_livro)
        conexao.commit()

        registrar_log(f"/livros/{id_livro}", "DELETE", registro_deletado_json, "SUCESSO", id_gerado=id_livro)
        return {"mensagem": "Livro removido com sucesso!", "IdLivro": id_livro}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/{id_livro}", "DELETE", None, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()

@app.post("/livros/delete-batch", dependencies=[Depends(verificar_api_key)])
def deletar_livros_em_lote(entrada: DeleteLoteEntrada):
    resultados = []
    for id_livro in entrada.ids:
        conexao = get_conexao()
        cursor = conexao.cursor()
        try:
            cursor.execute("SELECT * FROM Livro WHERE IdLivro = ?", id_livro)
            linha = cursor.fetchone()

            if linha is None:
                registrar_log(f"/livros/{id_livro}", "DELETE (lote)", None, "ERRO", mensagem_erro="Livro não encontrado")
                resultados.append({"IdLivro": id_livro, "status": "ERRO", "motivo": "Livro não encontrado"})
                continue

            colunas = [coluna[0] for coluna in cursor.description]
            registro_deletado = dict(zip(colunas, linha))
            registro_deletado_json = json.dumps(registro_deletado, default=str)

            cursor.execute("DELETE FROM Livro WHERE IdLivro = ?", id_livro)
            conexao.commit()

            registrar_log(f"/livros/{id_livro}", "DELETE (lote)", registro_deletado_json, "SUCESSO", id_gerado=id_livro)
            resultados.append({"IdLivro": id_livro, "status": "SUCESSO"})

        except pyodbc.Error as e:
            conexao.rollback()
            registrar_log(f"/livros/{id_livro}", "DELETE (lote)", None, "ERRO", mensagem_erro=str(e))
            resultados.append({"IdLivro": id_livro, "status": "ERRO", "motivo": str(e)})

        finally:
            conexao.close()

    total_sucesso = len([r for r in resultados if r["status"] == "SUCESSO"])
    total_erro = len([r for r in resultados if r["status"] == "ERRO"])

    return {
        "mensagem": f"Processado: {total_sucesso} removido(s), {total_erro} com erro.",
        "detalhes": resultados
    }

@app.post("/livros/importar/{isbn}", dependencies=[Depends(verificar_api_key)])
def importar_livro(isbn: str, preco: float = 0.00):
    resposta_google = requests.get(
    "https://www.googleapis.com/books/v1/volumes",
    params={"q": f"isbn:{isbn}", "key": GOOGLE_BOOKS_API_KEY}
)
    dados_google = resposta_google.json()

    if "items" not in dados_google:
        registrar_log(f"/livros/importar/{isbn}", "POST", None, "ERRO", mensagem_erro="Livro não encontrado na Google Books API")
        raise HTTPException(status_code=404, detail="Livro não encontrado na Google Books API")

    volume_info = dados_google["items"][0]["volumeInfo"]

    nome_livro = volume_info.get("title", "Título não informado")
    editora_texto = volume_info.get("publisher")
    assunto_texto = volume_info.get("categories", [None])[0]
    data_pub = tratar_data_publicacao(volume_info.get("publishedDate"))
    numero_paginas = volume_info.get("pageCount", 0)

    payload_json = json.dumps(volume_info, default=str)

    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        id_editora = buscar_ou_criar_editora(editora_texto, cursor, conexao)
        id_assunto = buscar_ou_criar_assunto(assunto_texto, cursor, conexao)

        cursor.execute("""
            INSERT INTO Livro (NomeLivro, ISBN13, DataPub, PrecoLivro, NumeroPaginas, IdEditora, IdAssunto, Edicao)
            OUTPUT INSERTED.IdLivro
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, nome_livro, isbn, data_pub, preco, numero_paginas, id_editora, id_assunto, 1)

        novo_id = cursor.fetchone()[0]
        conexao.commit()

        registrar_log(f"/livros/importar/{isbn}", "POST", payload_json, "SUCESSO", id_gerado=novo_id)

        return {
            "mensagem": "Livro importado com sucesso da Google Books API!",
            "IdLivro": novo_id,
            "NomeLivro": nome_livro,
            "Editora": editora_texto,
            "Assunto": assunto_texto
        }

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/importar/{isbn}", "POST", payload_json, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()

@app.get("/editoras")
def listar_editoras():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT IdEditora, NomeEditora FROM Editora ORDER BY NomeEditora")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado

@app.get("/assuntos")
def listar_assuntos():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT IdAssunto, NomeAssunto FROM Assunto ORDER BY NomeAssunto")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado

@app.get("/logs")
def listar_logs():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM LogIntegracao ORDER BY DataHora DESC")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado