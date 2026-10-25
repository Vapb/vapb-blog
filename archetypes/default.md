---
# máx. 60 caracteres (scripts/check_titles.py); o resto vai em description
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: true
---

