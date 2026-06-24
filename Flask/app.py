import os
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from supabase import Client, create_client


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Configure as variaveis de ambiente SUPABASE_URL e SUPABASE_KEY."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else None
)


def user_supabase_client():
    access_token = session.get("access_token")
    if not access_token:
        return None

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(access_token)
    return client


def require_notes_client():
    user_id = current_user_id()
    client = supabase_admin or user_supabase_client()

    if not client or not user_id:
        return None, None, (jsonify({"error": "Usuario nao autenticado."}), 401)

    return client, user_id, None


def error_details(exc):
    details = str(exc)
    code = getattr(exc, "code", None)
    message = getattr(exc, "message", None)

    if message and message not in details:
        details = f"{message} ({details})"

    return {"detalhes": details, "codigo": code}


def current_user_id():
    return session.get("user_id")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user_id():
            if request.path.startswith("/api/"):
                return jsonify({"error": "Usuario nao autenticado."}), 401
            return redirect(url_for("login_page"))

        return view(*args, **kwargs)

    return wrapped_view


def auth_payload():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return None, jsonify({"error": "Email e senha sao obrigatorios."}), 400

    return {"email": email, "password": password}, None, None


def store_auth_session(auth_response):
    user = getattr(auth_response, "user", None)
    auth_session = getattr(auth_response, "session", None)

    if not user or not auth_session:
        return False

    session.clear()
    session["user_id"] = user.id
    session["access_token"] = auth_session.access_token
    session["refresh_token"] = auth_session.refresh_token
    return True


def first_response_row(data):
    if isinstance(data, list):
        return data[0] if data else None

    return data


def note_belongs_to_user(note_id, user_id):
    response = (
        supabase.table("notes")
        .select("id")
        .eq("id", note_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return bool(response.data)


@app.get("/")
@login_required
def index():
    return render_template("index.html")


@app.get("/login")
def login_page():
    if current_user_id():
        return redirect(url_for("index"))

    return render_template("login.html")


@app.post("/register")
def register():
    payload, error_response, status_code = auth_payload()
    if error_response:
        return error_response, status_code

    try:
        response = supabase.auth.sign_up(payload)
        if not store_auth_session(response):
            return (
                jsonify(
                    {
                        "message": "Cadastro criado. Confirme seu email para entrar.",
                        "requires_confirmation": True,
                        "redirect": False,
                        "user": getattr(response.user, "id", None),
                    }
                ),
                201,
            )

        return jsonify({"message": "Usuario cadastrado com sucesso.", "redirect": True}), 201
    except Exception as exc:
        return jsonify({"error": "Erro ao cadastrar usuario.", "details": str(exc)}), 400


@app.post("/login")
def login():
    payload, error_response, status_code = auth_payload()
    if error_response:
        return error_response, status_code

    try:
        response = supabase.auth.sign_in_with_password(payload)
        if not store_auth_session(response):
            return jsonify({"error": "Credenciais invalidas."}), 401

        return jsonify({"message": "Login realizado com sucesso.", "redirect": True})
    except Exception as exc:
        return jsonify({"error": "Erro ao autenticar usuario.", "details": str(exc)}), 401


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.get("/api/notes")
@login_required
def list_notes():
    try:
        db, user_id, auth_error = require_notes_client()
        if auth_error:
            return auth_error

        response = (
            db.table("notes")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return jsonify({"notes": response.data or []})
    except Exception as e:
        return jsonify({"error": "Erro ao buscar notas.", **error_details(e)}), 500


@app.route("/api/notes", methods=["POST"])
@login_required
def create_note():
    try:
        db, user_id, auth_error = require_notes_client()
        if auth_error:
            return auth_error

        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload JSON nao recebido ou invalido"}), 400

        title = data.get("title", "Sem titulo")
        content = data.get("content", "")

        nova_nota = {
            "title": title,
            "content": content,
            "user_id": user_id,
        }

        response = db.table("notes").insert(nova_nota).select("*").execute()
        created_note = first_response_row(response.data)

        if not created_note:
            return (
                jsonify(
                    {
                        "error": "Nota criada, mas o Supabase nao retornou os dados.",
                        "hint": "Verifique se existe uma policy SELECT para o usuario autenticado.",
                    }
                ),
                500,
            )

        return jsonify({"success": True, "note": created_note, "data": response.data}), 201
    except Exception as exc:
        return jsonify(
            {
                "error": "Erro interno no Flask ao falar com o Supabase",
                **error_details(exc),
                "hint": (
                    "Se aparecer row-level security, configure SUPABASE_SERVICE_KEY no .env "
                    "ou rode novamente o SQL das policies no Supabase."
                ),
            }
        ), 500


@app.put("/api/notes/<note_id>")
@login_required
def update_note(note_id):
    try:
        db, user_id, auth_error = require_notes_client()
        if auth_error:
            return auth_error

        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload JSON nao recebido ou invalido"}), 400

        updates = {
            "title": (data.get("title") or "Sem titulo").strip(),
            "content": data.get("content") or "",
        }

        response = (
            db.table("notes")
            .update(updates)
            .eq("id", note_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            return jsonify({"error": "Nota nao encontrada ou sem permissao."}), 404

        return jsonify({"success": True, "data": response.data}), 200
    except Exception as e:
        return jsonify({"error": "Erro ao atualizar nota.", **error_details(e)}), 500


@app.delete("/api/notes/<note_id>")
@login_required
def delete_note(note_id):
    try:
        db, user_id, auth_error = require_notes_client()
        if auth_error:
            return auth_error

        response = (
            db.table("notes")
            .delete()
            .eq("id", note_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            return jsonify({"error": "Nota nao encontrada ou sem permissao."}), 404

        return jsonify({"success": True, "data": response.data}), 200
    except Exception as e:
        return jsonify({"error": "Erro ao deletar nota.", **error_details(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
