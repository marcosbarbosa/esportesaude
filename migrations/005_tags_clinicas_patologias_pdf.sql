-- ==============================================================================
-- IMBRA — Seed: Tags Clínicas (novas) + Vínculos aluno ↔ tags_saude
-- Fonte: PDF "Patologias - Anamnese Clinica" — 107 alunos — 29/07/2026
-- Execute no Supabase Dashboard → SQL Editor
-- Idempotente: WHERE NOT EXISTS nas novas tags | UPDATE direto nas tags_saude
-- ==============================================================================

-- ── 0. Desabilitar RLS ────────────────────────────────────────────────────────
ALTER TABLE IF EXISTS tags_clinicas_sistema DISABLE ROW LEVEL SECURITY;


-- ── 1. Novas tags clínicas (as 14 existentes são preservadas) ─────────────────
-- Inserção condicional: só insere se a tag ainda não existir pelo nome

INSERT INTO tags_clinicas_sistema (nome, icone, cor, tipo_alerta, ordem, dica_treino)
SELECT * FROM (VALUES
    (
        'Parkinson',
        '🫨', '#4F46E5', 'error', 15,
        'EVITAR: exercícios que exijam equilíbrio sem suporte, ambientes com obstáculos no chão, movimentos bruscos e mudanças de direção rápidas. '
        'EXECUTAR: exercícios rítmicos (dança, marcha cadenciada), treino de equilíbrio com apoio, alongamentos de tronco e membros. '
        'Supervisão próxima em todas as sessões. Monitorar rigidez e tremor antes de iniciar.'
    ),
    (
        'Problemas na Coluna / Hérnia de Disco',
        '🧘', '#78716C', 'warning', 16,
        'EVITAR: flexão excessiva da coluna lombar (abdominais tradicionais, curvamento abrupto), cargas axiais pesadas, rotações bruscas. '
        'EXECUTAR: fortalecimento do core (prancha com tempo limitado, bird-dog), mobilidade controlada, exercícios na água. '
        'Toda atividade deve respeitar a amplitude sem dor. Adaptar conforme localização (cervical/lombar) e sintomas do dia.'
    ),
    (
        'Rinite / Sinusite Alérgica',
        '🤧', '#0EA5E9', 'info', 17,
        'EVITAR: ambientes com pó excessivo, odores fortes, ar muito seco ou frio sem aquecimento prévio das vias aéreas. '
        'EXECUTAR: aquecimento respiratório antes do exercício, hidratação constante. '
        'Manter broncodilatador disponível se necessário. Adaptar intensidade em dias de crise.'
    ),
    (
        'Ácido Úrico / Gota',
        '🦵', '#7C3AED', 'warning', 18,
        'EVITAR: exercícios de alta intensidade em períodos de crise gotosa (dor articular aguda), desidratação. '
        'EXECUTAR: atividades de baixo impacto (natação, bicicleta), hidratação abundante durante toda a sessão. '
        'Em crise: suspender atividade e encaminhar para avaliação médica. Fora da crise: exercício regular melhora controle metabólico.'
    ),
    (
        'Tremor Essencial',
        '🫨', '#6B7280', 'info', 19,
        'EVITAR: exercícios que exijam precisão motora fina em situações de cansaço (risco de frustração). '
        'EXECUTAR: atividades rítmicas e previsíveis, exercícios de coordenação adaptados, treino de força com movimentos amplos e controlados. '
        'Adaptar implementos (pesos com alça, faixas elásticas) para melhorar a aderência. Monitorar progressão do tremor ao longo da sessão.'
    )
) AS v(nome, icone, cor, tipo_alerta, ordem, dica_treino)
WHERE NOT EXISTS (
    SELECT 1 FROM tags_clinicas_sistema t WHERE t.nome = v.nome
);


-- ==============================================================================
-- ── 2. Vínculo aluno ↔ tags_saude (UPDATE no campo texto do aluno)
-- Cada UPDATE só executa se o aluno existe na base de ativos.
-- Tags separadas por vírgula — nomes EXATOS do catálogo tags_clinicas_sistema.
-- Alunos sem condição identificada no PDF não são tocados.
-- ==============================================================================

-- ADRIANA BEATRIZ PERIN — Acompanhamento pós câncer
UPDATE alunos SET tags_saude = 'Câncer (tratamento/remissão)'
WHERE nome ILIKE '%ADRIANA BEATRIZ PERIN%' AND status != 'Inativo';

-- ADRIANA MARIA LERRO — Asma, hipertensão, pré-diabetes
UPDATE alunos SET tags_saude = 'DPOC/Asma,Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%ADRIANA MARIA LERRO%' AND status != 'Inativo';

-- ADRIANA SILVA SANTOS — Pré-diabética
UPDATE alunos SET tags_saude = 'Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%ADRIANA SILVA SANTOS%' AND status != 'Inativo';

-- AKIO URATA — Pressão controlada, Diabetes controlada, Parkinson
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes,Parkinson'
WHERE nome ILIKE '%AKIO URATA%' AND status != 'Inativo';

-- ANA CAROLINA LINS CORREIA DE MELO — Diabete
UPDATE alunos SET tags_saude = 'Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%ANA CAROLINA LINS%' AND status != 'Inativo';

-- ANGELA MARIA FRANCESCON DIAS — Fibromialgia, hipotireoidismo, hipertensão
UPDATE alunos SET tags_saude = 'Fibromialgia,Hipotireoidismo / Hashimoto,Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%ANGELA MARIA FRANCESCON%' AND status != 'Inativo';

-- ANGELA MARIA SOARES ROMANO — Paroxetina (antidepressivo/ansiolítico)
UPDATE alunos SET tags_saude = 'Ansiedade / Depressão'
WHERE nome ILIKE '%ANGELA MARIA SOARES ROMANO%' AND status != 'Inativo';

-- APARECIDA EDNA DE SOUZA — Rinite alérgica
UPDATE alunos SET tags_saude = 'Rinite / Sinusite Alérgica'
WHERE nome ILIKE '%APARECIDA EDNA DE SOUZA%' AND status != 'Inativo';

-- APARECIDA ODETE DELFINO — Pressão alta, pré-diabetes, colesterol alto
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes,Colesterol Alto / Dislipidemia'
WHERE nome ILIKE '%APARECIDA ODETE DELFINO%' AND status != 'Inativo';

-- BENILDA ANTÔNIA DE MELO SANTOS — Ansiedade
UPDATE alunos SET tags_saude = 'Ansiedade / Depressão'
WHERE nome ILIKE '%BENILDA ANTÔNIA DE MELO%' AND status != 'Inativo';

-- CARLOS ALBERTO TAVARES — Ácido úrico
UPDATE alunos SET tags_saude = 'Ácido Úrico / Gota'
WHERE nome ILIKE '%CARLOS ALBERTO TAVARES%' AND status != 'Inativo';

-- CARMELITA LIMA DE OLIVEIRA — Hipotireoidismo (medicamento pretireoide)
UPDATE alunos SET tags_saude = 'Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%CARMELITA LIMA DE OLIVEIRA%' AND status != 'Inativo';

-- CARMELITA MARIA DE OLIVEIRA SANTOS — Infarto recente, pressão, colesterol, pré-diabete, tireoide
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Colesterol Alto / Dislipidemia,Diabetes Mellitus Tipo II / Pré-diabetes,Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%CARMELITA MARIA DE OLIVEIRA SANTOS%' AND status != 'Inativo';

-- CARMEN LUCIA SANCHES RODRIGUES DA FONSECA — Condromalácia patelar, desgaste, lombar, cervical
UPDATE alunos SET tags_saude = 'Artrose/Artrite/Condromalácia,Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%CARMEN LUCIA SANCHES%' AND status != 'Inativo';

-- CLAUDIA MARIA ELIZABETH DUARTE LEME GOMES — Pré-diabético, colesterol
UPDATE alunos SET tags_saude = 'Diabetes Mellitus Tipo II / Pré-diabetes,Colesterol Alto / Dislipidemia'
WHERE nome ILIKE '%CLAUDIA MARIA ELIZABETH DUARTE%' AND status != 'Inativo';

-- CRISTINA CESAR PENTEADO EWAD — Hipertensão, hipotireoidismo
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%CRISTINA CESAR PENTEADO%' AND status != 'Inativo';

-- DARCI RAMIL SFORCINI — Artrose, osteoporose, refluxo
UPDATE alunos SET tags_saude = 'Artrose/Artrite/Condromalácia,Osteoporose'
WHERE nome ILIKE '%DARCI RAMIL SFORCINI%' AND status != 'Inativo';

-- DARCI RECUPERO — Pressão, colesterol, reumatismo (= artrite)
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Colesterol Alto / Dislipidemia,Artrose/Artrite/Condromalácia'
WHERE nome ILIKE '%DARCI RECUPERO%' AND status != 'Inativo';

-- DEISY APARECIDA DOMICIANO — Arritmia controlada
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%DEISY APARECIDA DOMICIANO%' AND status != 'Inativo';

-- DORIVAL SFORCINI — Pressão, coração, glicemia, pulmão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes,DPOC/Asma'
WHERE nome ILIKE '%DORIVAL SFORCINI%' AND status != 'Inativo';

-- ELENITA PEREIRA SANTOS BRAGA — Pressão alta, pré-diabética
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%ELENITA PEREIRA SANTOS BRAGA%' AND status != 'Inativo';

-- ELISANGELA MENDES MARCAL OSES — Síndrome de Hashimoto
UPDATE alunos SET tags_saude = 'Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%ELISANGELA MENDES MARCAL%' AND status != 'Inativo';

-- ELIZABETH GARCIA LUCAS — Tendinite, inflamação do ciático
UPDATE alunos SET tags_saude = 'Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%ELIZABETH GARCIA LUCAS%' AND status != 'Inativo';

-- EUNICE MELLEIRO CORTEZ — Pressão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%EUNICE MELLEIRO CORTEZ%' AND status != 'Inativo';

-- FELIPE PIRES FRACCAROLI DAHER — Autismo
UPDATE alunos SET tags_saude = 'Autismo'
WHERE nome ILIKE '%FELIPE PIRES FRACCAROLI%' AND status != 'Inativo';

-- HAMILTON FERREIRA LEONE — Pressão alta
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%HAMILTON FERREIRA LEONE%' AND status != 'Inativo';

-- HAROLDO CEZAR LEHMANN — Hipertensão (medicamento Aradois)
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%HAROLDO CEZAR LEHMANN%' AND status != 'Inativo';

-- HILDA DE MARIA ALMEIDA TEIXEIRA — Pressão controlada
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%HILDA DE MARIA ALMEIDA%' AND status != 'Inativo';

-- IRANDIR MENDES RIBEIRO — Colesterol e pré-diabética
UPDATE alunos SET tags_saude = 'Colesterol Alto / Dislipidemia,Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%IRANDIR MENDES RIBEIRO%' AND status != 'Inativo';

-- ISAURA PIRES BOLONHA — Cardíaca, nódulo na tireoide
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%ISAURA PIRES BOLONHA%' AND status != 'Inativo';

-- JADINA SEVERINA DA SILVA — Osteoporose, cirurgia femural, prótese
UPDATE alunos SET tags_saude = 'Osteoporose'
WHERE nome ILIKE '%JADINA SEVERINA DA SILVA%' AND status != 'Inativo';

-- JERUSIA PERES — Pressão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%JERUSIA PERES%' AND status != 'Inativo';

-- JOSE ANTONIO MIGUEL RODRIGUES — Colesterol
UPDATE alunos SET tags_saude = 'Colesterol Alto / Dislipidemia'
WHERE nome ILIKE '%JOSE ANTONIO MIGUEL RODRIGUES%' AND status != 'Inativo';

-- JOSÉ SÉRGIO LONGO — Cardíaco, pressão alta
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%JOSÉ SÉRGIO LONGO%' AND status != 'Inativo';

-- LUCIA MARIA BRANCO CABRAL — Tireoide e joelho
UPDATE alunos SET tags_saude = 'Hipotireoidismo / Hashimoto,Artrose/Artrite/Condromalácia'
WHERE nome ILIKE '%LUCIA MARIA BRANCO CABRAL%' AND status != 'Inativo';

-- MAGDA MAIA MORAES — Artrose, Hashimoto, colesterol alto
UPDATE alunos SET tags_saude = 'Artrose/Artrite/Condromalácia,Hipotireoidismo / Hashimoto,Colesterol Alto / Dislipidemia'
WHERE nome ILIKE '%MAGDA MAIA MORAES%' AND status != 'Inativo';

-- MÁRCIA DA SILVA COIMBRÃ — Colesterol, câncer de mama (histórico)
UPDATE alunos SET tags_saude = 'Colesterol Alto / Dislipidemia,Câncer (tratamento/remissão)'
WHERE nome ILIKE '%MÁRCIA DA SILVA COIMBR%' AND status != 'Inativo';

-- MARCIA REGINA DE SOUZAZWLLER — Hipertensa, arritmia
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%MARCIA REGINA DE SOUZA%' AND status != 'Inativo';

-- MARIA ADRIANA DE SOUZA FARIAS — Lesão no joelho, coluna, ombro
UPDATE alunos SET tags_saude = 'Artrose/Artrite/Condromalácia,Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%MARIA ADRIANA DE SOUZA FARIAS%' AND status != 'Inativo';

-- MARIA APARECIDA DA SILVA LUCAS — Colesterol, ossos (osteoporose)
UPDATE alunos SET tags_saude = 'Colesterol Alto / Dislipidemia,Osteoporose'
WHERE nome ILIKE '%MARIA APARECIDA DA SILVA LUCAS%' AND status != 'Inativo';

-- MARIA CRISTINA VALDÉS DE ESTÉVEZ — Diabetes tipo 2
UPDATE alunos SET tags_saude = 'Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%MARIA CRISTINA VALDÉS%' AND status != 'Inativo';

-- MARIA DE LOURDES PINHA LEITÃO GONÇALVES — Pressão alta e ansiedade
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Ansiedade / Depressão'
WHERE nome ILIKE '%MARIA DE LOURDES PINHA%' AND status != 'Inativo';

-- MARIA DE LURDES DA SILVA — Pressão, asma e pré-diabética
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),DPOC/Asma,Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%MARIA DE LURDES DA SILVA%' AND status != 'Inativo';

-- MARIA DO CARMO SOUZA FERRERI — Hipertensão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%MARIA DO CARMO SOUZA FERRER%' AND status != 'Inativo';

-- MARIA DO ROSÁRIO SOUSA — Diabetes
UPDATE alunos SET tags_saude = 'Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%MARIA DO ROSÁRIO SOUSA%' AND status != 'Inativo';

-- MÁRIA DOLORES DE SOUSA PESSOA — Pressão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%DOLORES DE SOUSA PESSOA%' AND status != 'Inativo';

-- MARIA INOCENCIA NOGUEIRA DRAUNE — Pressão alta emocional, retenção, varizes
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%MARIA INOCENCIA NOGUEIRA%' AND status != 'Inativo';

-- MARIA LIGIA DE CASTRO MARINS — Pressão alta, hipotireoidismo, depressão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Hipotireoidismo / Hashimoto,Ansiedade / Depressão'
WHERE nome ILIKE '%MARIA LIGIA DE CASTRO%' AND status != 'Inativo';

-- MARIA LUISA CAETANO — Pressão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%MARIA LUISA CAETANO%' AND status != 'Inativo';

-- MARIA ROSA LOPES QUINGOSTAS — Pressão alta, colesterol, diabetes
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Colesterol Alto / Dislipidemia,Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%MARIA ROSA LOPES QUINGOSTAS%' AND status != 'Inativo';

-- MARIA SOCORRO MEDEIROS HOSHINO — Desgaste lombar, dor no ombro
UPDATE alunos SET tags_saude = 'Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%MARIA SOCORRO MEDEIROS%' AND status != 'Inativo';

-- MARIA TERESA MARQUES ARAÚJO — Hipertensão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%MARIA TERESA MARQUES ARAÚJO%' AND status != 'Inativo';

-- MARIANGELA NAPONIELLO — Rinite alérgica, sinusite
UPDATE alunos SET tags_saude = 'Rinite / Sinusite Alérgica'
WHERE nome ILIKE '%MARIANGELA NAPONIELLO%' AND status != 'Inativo';

-- MARILICE FERNANDES BERTOLINI — Artrose
UPDATE alunos SET tags_saude = 'Artrose/Artrite/Condromalácia'
WHERE nome ILIKE '%MARILICE FERNANDES BERTOLINI%' AND status != 'Inativo';

-- MARISA SAAVEDRA NUNES — Ansiedade
UPDATE alunos SET tags_saude = 'Ansiedade / Depressão'
WHERE nome ILIKE '%MARISA SAAVEDRA NUNES%' AND status != 'Inativo';

-- MARLI DELIBERADOR MICKOSZ — Pressão alta, diabetes, tireoide
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes,Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%MARLI DELIBERADOR%' AND status != 'Inativo';

-- MELAINE CAROLINA PIZANE — Câncer de mama (6 anos atrás, acompanhamento semestral)
UPDATE alunos SET tags_saude = 'Câncer (tratamento/remissão)'
WHERE nome ILIKE '%MELAINE CAROLINA PIZANE%' AND status != 'Inativo';

-- MONICA VALLS INDALENCIA MOREIRA — Cirurgia de coração recente, pressão controlada
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%MONICA VALLS%' AND status != 'Inativo';

-- NILSON VARELA MASCARENHAS — Próstata e coração (acompanhamento)
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%NILSON VARELA MASCARENHAS%' AND status != 'Inativo';

-- NIVEA AMARAL MOREIRA — Pressão alta, diabetes, colesterol, varizes, artrose, hipotireoidismo
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes,Colesterol Alto / Dislipidemia,Artrose/Artrite/Condromalácia,Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%NIVEA AMARAL MOREIRA%' AND status != 'Inativo';

-- PEDRINA MARIA DE JESUS — Pressão alta, colesterol e refluxo
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Colesterol Alto / Dislipidemia'
WHERE nome ILIKE '%PEDRINA MARIA DE JESUS%' AND status != 'Inativo';

-- QUITÉRIA MENDES DA SILVA — Pressão alta
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%QUITÉRIA MENDES DA SILVA%' AND status != 'Inativo';

-- REGINA LIMA DA SILVA — Pressão alta, pré-diabetes, coluna lombar
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Diabetes Mellitus Tipo II / Pré-diabetes,Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%REGINA LIMA DA SILVA%' AND status != 'Inativo';

-- RENATA SONCINI FACCI — Tremor essencial
UPDATE alunos SET tags_saude = 'Tremor Essencial'
WHERE nome ILIKE '%RENATA SONCINI FACCI%' AND status != 'Inativo';

-- SILVANA CAMPOS OLIVEIRA — Pressão alta, sem tireoide (hipotireoidismo cirúrgico)
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%SILVANA CAMPOS OLIVEIRA%' AND status != 'Inativo';

-- SÍLVIA CRISTINA DOS SANTOS MAZZA — Dor lombar
UPDATE alunos SET tags_saude = 'Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%SÍLVIA CRISTINA DOS SANTOS%' AND status != 'Inativo';

-- SILVIA REGINA MAZZOCO MADDALONI — Colesterol, esofagite, artrose
UPDATE alunos SET tags_saude = 'Colesterol Alto / Dislipidemia,Artrose/Artrite/Condromalácia'
WHERE nome ILIKE '%SILVIA REGINA MAZZOCO%' AND status != 'Inativo';

-- SONIA MARIA DA CUNHA — Pressão, tireoide e diabetes
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia),Hipotireoidismo / Hashimoto,Diabetes Mellitus Tipo II / Pré-diabetes'
WHERE nome ILIKE '%SONIA MARIA DA CUNHA%' AND status != 'Inativo';

-- SONIA MARIA FERNANDES NUNES DA SILVA — Hipertensão controlada, deficiência auditiva
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%SONIA MARIA FERNANDES NUNES%' AND status != 'Inativo';

-- THEREZINHA NAZARÉ CURY TEIXEIRA ANHAUCI — AVC controlado
UPDATE alunos SET tags_saude = 'AVC Controlado'
WHERE nome ILIKE '%THEREZINHA NAZARÉ CURY%' AND status != 'Inativo';

-- THEREZINHA RIBEIRO CANTO — Pressão
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%THEREZINHA RIBEIRO CANTO%' AND status != 'Inativo';

-- VALDINEI RODRIGUES DOS SANTOS — Pressão arterial
UPDATE alunos SET tags_saude = 'Hipertensão/Cardiopatia (inclui Arritmia)'
WHERE nome ILIKE '%VALDINEI RODRIGUES DOS SANTOS%' AND status != 'Inativo';

-- VANESSA MARIA CARVALHO ATHAYDE CORREIA — Hérnia de disco
UPDATE alunos SET tags_saude = 'Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%VANESSA MARIA CARVALHO ATHAYDE%' AND status != 'Inativo';

-- VANI ROCHA LEONE — Hipotireoidismo (medicamento puran)
UPDATE alunos SET tags_saude = 'Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%VANI ROCHA LEONE%' AND status != 'Inativo';

-- VERA REGINA ABONDANZA — Dor na lombar
UPDATE alunos SET tags_saude = 'Problemas na Coluna / Hérnia de Disco'
WHERE nome ILIKE '%VERA REGINA ABONDANZA%' AND status != 'Inativo';

-- VIVIANE CARDOSO — Hipotireoidismo
UPDATE alunos SET tags_saude = 'Hipotireoidismo / Hashimoto'
WHERE nome ILIKE '%VIVIANE CARDOSO%' AND status != 'Inativo';


-- ==============================================================================
-- ── 3. Verificação — descomente para conferir ────────────────────────────────
-- ==============================================================================
/*
-- Total de alunos com tags_saude preenchido:
SELECT COUNT(*) AS com_tags FROM alunos WHERE tags_saude IS NOT NULL AND tags_saude != '' AND status != 'Inativo';

-- Distribuição por tag (quais são mais frequentes):
SELECT tag, COUNT(*) AS qtd
FROM (
    SELECT TRIM(UNNEST(STRING_TO_ARRAY(tags_saude, ','))) AS tag
    FROM alunos WHERE tags_saude IS NOT NULL AND status != 'Inativo'
) t
GROUP BY tag ORDER BY qtd DESC;

-- Alunos com suas tags:
SELECT nome, tags_saude FROM alunos WHERE tags_saude IS NOT NULL AND tags_saude != '' AND status != 'Inativo' ORDER BY nome;
*/
