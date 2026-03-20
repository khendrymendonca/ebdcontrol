-- ============================================================
-- LOGOS — Script de criação das tabelas no Supabase
-- Execute no SQL Editor do painel Supabase
-- ============================================================

-- 1. Perfis dos usuários (vinculado ao auth.users do Supabase)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  email TEXT,
  tipo TEXT NOT NULL CHECK (tipo IN ('professor', 'aluno')) DEFAULT 'aluno',
  data_nasc DATE,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Turmas
CREATE TABLE IF NOT EXISTS turmas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome TEXT NOT NULL,
  professor_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  ano TEXT DEFAULT '2025',
  semestre TEXT DEFAULT '1',
  descricao TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Matrícula de alunos em turmas
CREATE TABLE IF NOT EXISTS turma_alunos (
  turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE,
  aluno_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  PRIMARY KEY (turma_id, aluno_id)
);

-- 4. Presenças
CREATE TABLE IF NOT EXISTS presencas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aluno_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE,
  data DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('presente', 'falta', 'justificada')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (aluno_id, turma_id, data)
);

-- 5. Materiais / PDFs
CREATE TABLE IF NOT EXISTS materiais (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  titulo TEXT NOT NULL,
  descricao TEXT,
  arquivo_url TEXT,
  turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE,
  visivel BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Provas
CREATE TABLE IF NOT EXISTS provas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  titulo TEXT NOT NULL,
  descricao TEXT,
  turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE,
  peso NUMERIC DEFAULT 10,
  data DATE,
  visivel BOOLEAN DEFAULT FALSE,
  questoes_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Respostas de provas
CREATE TABLE IF NOT EXISTS respostas_prova (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aluno_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  prova_id UUID REFERENCES provas(id) ON DELETE CASCADE,
  respostas_json JSONB,
  nota NUMERIC,
  feedback TEXT,
  corrigida BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (aluno_id, prova_id)
);

-- 8. Trabalhos
CREATE TABLE IF NOT EXISTS trabalhos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  titulo TEXT NOT NULL,
  descricao TEXT,
  turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE,
  prazo DATE,
  peso NUMERIC DEFAULT 10,
  visivel BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Entregas de trabalhos
CREATE TABLE IF NOT EXISTS entregas_trabalho (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aluno_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  trabalho_id UUID REFERENCES trabalhos(id) ON DELETE CASCADE,
  arquivo_url TEXT,
  data_entrega DATE DEFAULT CURRENT_DATE,
  nota NUMERIC,
  feedback TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE turmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE turma_alunos ENABLE ROW LEVEL SECURITY;
ALTER TABLE presencas ENABLE ROW LEVEL SECURITY;
ALTER TABLE materiais ENABLE ROW LEVEL SECURITY;
ALTER TABLE provas ENABLE ROW LEVEL SECURITY;
ALTER TABLE respostas_prova ENABLE ROW LEVEL SECURITY;
ALTER TABLE trabalhos ENABLE ROW LEVEL SECURITY;
ALTER TABLE entregas_trabalho ENABLE ROW LEVEL SECURITY;

-- Profiles: todos podem ler os seus próprios dados
CREATE POLICY "profiles_self" ON profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "profiles_read_all" ON profiles FOR SELECT USING (true);

-- Turmas: professor vê as suas, aluno vê as que está matriculado
CREATE POLICY "turmas_professor" ON turmas FOR ALL USING (
  professor_id = auth.uid()
);
CREATE POLICY "turmas_aluno" ON turmas FOR SELECT USING (
  EXISTS (SELECT 1 FROM turma_alunos WHERE turma_id = id AND aluno_id = auth.uid())
);

-- Materiais visíveis para alunos da turma
CREATE POLICY "materiais_aluno" ON materiais FOR SELECT USING (
  visivel = TRUE AND EXISTS (
    SELECT 1 FROM turma_alunos WHERE turma_id = materiais.turma_id AND aluno_id = auth.uid()
  )
);
CREATE POLICY "materiais_professor" ON materiais FOR ALL USING (
  EXISTS (SELECT 1 FROM turmas WHERE id = turma_id AND professor_id = auth.uid())
);

-- ============================================================
-- STORAGE BUCKETS (execute no painel Storage do Supabase)
-- ============================================================
-- Crie dois buckets públicos:
--   "materiais" → para PDFs das aulas
--   "trabalhos" → para entregas dos alunos

-- ============================================================
-- FUNÇÃO: auto-criar perfil ao registrar usuário
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email, nome, tipo)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'nome', split_part(NEW.email, '@', 1)),
    COALESCE(NEW.raw_user_meta_data->>'tipo', 'aluno')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
