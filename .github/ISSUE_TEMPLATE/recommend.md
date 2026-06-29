name: 推荐项目
description: 推荐一个有趣/入门级的开源项目
title: "[推荐] "
labels: ["recommendation"]
body:
  - type: input
    id: project_name
    attributes:
      label: 项目名称
      description: 项目名称和 GitHub 链接
      placeholder: "例如：https://github.com/xxx/yyy"
    validations:
      required: true

  - type: textarea
    id: description
    attributes:
      label: 项目介绍
      description: 2-3 句话介绍这个项目，包括核心功能和亮点
      placeholder: "这是一个..."
    validations:
      required: true

  - type: dropdown
    id: language
    attributes:
      label: 主要语言
      options:
        - Python
        - JavaScript
        - TypeScript
        - Go
        - Rust
        - Java
        - C/C++
        - Swift
        - Kotlin
        - Ruby
        - PHP
        - 其他
    validations:
      required: true

  - type: textarea
    id: reason
    attributes:
      label: 推荐理由
      description: 为什么推荐它？有趣在哪？入门级？
      placeholder: "推荐它的原因是..."
    validations:
      required: false
