本项目需要配置的环境说明参见本文档Readme.txt。
本项目调用的非python内置库包括：gradio, pandas, numpy, PyPDF2, camelot, ghostscript, dashscope, pymysql, PIL, matplotlib。调用的python内置库包括：io, re, os, random, datetime, threading, queue, typing, http, urllib。
本项目需要配置的其他软件环境包括：MySQL数据库、GhostScripts。

以上软件和库安装完成后，需要在本项目的DataControl.py修改Link2BusinessReportDatabase函数中用于连接数据库的用户名和密码参数。以及在LLMControl.py文件中修改api_key。api_key的获取方式参见阿里云模型服务灵积文档：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key

环境配置完成后，使用python运行FrontEnd.py文件，将会自动在浏览器中打开UI页面。相关操作演示参见项目展示demo视频。

如有详细项目展示需求，或在环境配置和项目运行时遇到问题，可联系项目负责人：
董子玥 
Email：231300017@smail.nju.edu.cn 
QQ：3181531488
