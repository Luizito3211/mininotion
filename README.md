# mininotion

Mini app de notas com Flask e Supabase.

## Configuracao

Crie um arquivo `.env` dentro da pasta `Flask` com:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_anon_public_key
FLASK_SECRET_KEY=troque-por-uma-chave-secreta
```

No Supabase, rode o SQL de `Flask/supabase_schema.sql` em **SQL Editor** para criar a tabela `notes` e as policies de RLS.

Os cadastros de email e senha ficam no **Supabase Auth**, na tabela interna `auth.users`. Essa tabela nao aparece como uma tabela publica comum do seu app; por isso as notas usam `user_id` apontando para `auth.users(id)`.

Para exigir verificacao de email antes do login, ative a confirmacao de email em **Authentication > Providers > Email** no painel do Supabase.
