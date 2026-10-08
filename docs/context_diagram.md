```mermaid
%%{init: {'theme':'dark', 'themeVariables': { 'primaryColor':'#E6E6FA', 'primaryTextColor':'black', 'lineColor':'lightgrey', 'edgeLabelBackground':'#333', 'tertiaryColor':'black', 'background':'transparent'}, 'themeCSS': '.edgeLabel, .edgeLabel p, .edgeLabel rect { background-color: #1F1F1F !important; fill: #1F1F1F !important; }', 'flowchart': {'curve':'basis'}}}%%

graph TB
    classDef default fill:#E6E6FA,color:black,stroke:#C9B8E8,stroke-width:2px;

    Owner[Owner / Manager]:::default
    PWA[PWA React + Vite<br/>Mobile-first]:::default
    Backend[FastAPI Core]:::default
    LLM[Qwen External API<br/>OpenAI-compatible]:::default
    Scanner[Сканер ШК<br/>html5-qrcode]:::default

    DB[(PostgreSQL 15)]:::db

    Owner -->|HTTPS| PWA
    PWA -->|REST API<br/>Bearer JWT + X-Store-ID| Backend
    Scanner -->|Камера браузера| PWA

    Backend -->|SQLAlchemy Async| DB
    Backend -->|OpenAI API (Tool Calling)| LLM
    LLM -->|Function Calls| Backend

    linkStyle default stroke:lightgrey,stroke-width:2px,color:white;
```
