# Auto Typer

Aplicativo desktop em Python para automatizar o preenchimento de campos na tela em um horário programado, usando reconhecimento de imagem.

## Recursos

- Seleção de uma imagem de referência do campo.
- Captura de uma região da tela sem precisar criar a imagem manualmente.
- Agendamento por horário (`HH:MM` ou `HH:MM:SS`).
- Reconhecimento visual com sensibilidade ajustável.
- Colagem automática do texto com suporte a acentos.
- Pressionamento automático de `Enter` após preencher o campo.
- Cancelamento de agendamento.
- Log de atividade e status visual.
- Interface escura moderna feita com Tkinter/ttk.

## Requisitos

- Python 3.10 ou superior recomendado.
- Windows, macOS ou Linux.

## Instalação

```bash
git clone https://github.com/L7somente/auto-typer.git
cd auto-typer
python -m venv .venv
python -m pip install -r requirements.txt
```

No Windows, para ativar o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Executar

```bash
python auto_typer_app.py
```

## Como usar

1. Clique em **Selecionar arquivo** ou **Capturar da tela**.
2. Informe o texto que será enviado.
3. Defina o horário desejado.
4. Ajuste a sensibilidade de reconhecimento se necessário.
5. Clique em **Agendar automação**.
6. Mantenha a tela que contém o campo visível quando chegar o horário.

Se o horário informado já tiver passado no dia atual, a execução será agendada para o dia seguinte.

## Observações

No Windows, se o aplicativo que receberá a automação estiver aberto como administrador, talvez seja necessário abrir o Auto Typer também como administrador. No macOS, podem ser necessárias permissões de Acessibilidade e Gravação de Tela. Em Linux, X11 tende a funcionar melhor que Wayland para automação de mouse e captura de tela.

## Estrutura

```text
auto-typer/
├── auto_typer_app.py
├── requirements.txt
├── README.md
└── .gitignore
```
