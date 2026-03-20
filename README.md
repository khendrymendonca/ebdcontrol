# Logos 🎓 — Plataforma Educacional

App web mobile-first para gestão de turmas, desenvolvido com Python/Flask + Supabase + Vercel.

## Stack

- **Backend:** Python 3.12 + Flask (serverless no Vercel)
- **Banco:** Supabase (PostgreSQL)
- **Auth:** Supabase Auth
- **Storage:** Supabase Storage (PDFs, trabalhos)
- **Real-time:** Supabase JS SDK (atualização ao vivo no browser)
- **UI:** CSS mobile-first, glassmorphism, dark mode

## Setup Rápido

### 1. Clonar e configurar

```bash
cd logos
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 2. Variáveis de ambiente

Crie um arquivo `.env` baseado no `.env.example`:
```
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-anon-key
SUPABASE_SERVICE_KEY=sua-service-key
FLASK_SECRET_KEY=chave-secreta-forte-aqui
```

### 3. Configurar Supabase

1. Crie um projeto em [supabase.com](https://supabase.com)
2. Vá em **SQL Editor** e execute o arquivo `supabase_schema.sql`
3. Vá em **Storage** e crie dois buckets públicos: `materiais` e `trabalhos`
4. Copie a URL e as chaves API do painel **Settings → API**

### 4. Rodar localmente

```bash
python run.py
# Acesse: http://localhost:5000
```

### 5. Deploy no Vercel

```bash
npm install -g vercel
vercel login
vercel --prod
```

Configure as variáveis de ambiente no painel do Vercel (Settings → Environment Variables).

## Perfis de Usuário

| Perfil | Acesso |
|---|---|
| **Professor** | Tudo: dashboard, alunos, presença, materiais, provas, trabalhos, notas, visibilidade |
| **Aluno** | Apenas o que o professor habilitar: materiais, provas, trabalhos, notas pessoais |

## Módulos

- 📊 **Dashboard** — estatísticas, ranking, aniversariantes
- 👥 **Alunos** — criar, editar, matricular
- ✓ **Presença** — chamada diária com histórico
- 📄 **Materiais** — upload de PDFs e controle de visibilidade
- 📝 **Provas** — crie questões dissertativas e múltipla escolha
- 📁 **Trabalhos** — atividades com prazo e avaliação
- 📈 **Notas** — tabela de desempenho e ranking
- ⚡ **Real-time** — atualizações ao vivo via Supabase Realtime
