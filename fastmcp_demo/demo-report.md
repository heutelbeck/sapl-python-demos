# SAPL MCP Demo Report -- 2026-03-08 12:47:25 UTC

## Listings

### tools/list
| User | Visible Tools | Hidden (stealth) |
|------|---------------|------------------|
| mara | export_csv, list_data_exports, manage_pipelines, query_customer_data, query_public_data, run_model | purge_dataset |
| felix | list_data_exports, manage_pipelines, query_public_data, run_model | export_csv, purge_dataset, query_customer_data |
| diana | export_csv, list_data_exports, manage_pipelines, purge_dataset, query_customer_data, query_public_data, run_model | - |
| sam | list_data_exports, manage_pipelines, query_public_data, run_model | export_csv, purge_dataset, query_customer_data |
| anonymous | *(HTTP 401)* | - |

### resources/list
| User | Visible Resources | Hidden (stealth) |
|------|-------------------|------------------|
| mara | data://customers/segments, data://models/catalog, data://public/summary | data://audit/log |
| felix | data://models/catalog, data://public/summary | data://audit/log, data://customers/segments |
| diana | data://audit/log, data://customers/segments, data://models/catalog, data://public/summary | - |
| sam | data://models/catalog, data://public/summary | data://audit/log, data://customers/segments |
| anonymous | *(HTTP 401)* | - |

### prompts/list
| User | Visible Prompts |
|------|-----------------|
| mara | analyze_trends, compliance_review, generate_report |
| felix | analyze_trends, compliance_review, generate_report |
| diana | analyze_trends, compliance_review, generate_report |
| sam | analyze_trends, compliance_review, generate_report |
| anonymous | *(HTTP 401)* |

## Tool Calls

### query_public_data
| User | Decision | Details |
|------|----------|---------|
| mara | PERMIT | dataset, date_range, rows |
| felix | PERMIT | dataset, date_range, rows |
| diana | PERMIT | dataset, date_range, rows |
| sam | PERMIT | dataset, date_range, rows |
| anonymous | REJECT (HTTP 401) | - |

### query_customer_data
| User | Decision | Details |
|------|----------|---------|
| mara | PERMIT | segment, total_matches, limit |
| felix | DENY (Unknown tool: 'query_customer_data') | - |
| diana | PERMIT | segment, total_matches, limit |
| sam | DENY (Unknown tool: 'query_customer_data') | - |
| anonymous | REJECT (HTTP 401) | - |

### export_csv
| User | Decision | Details |
|------|----------|---------|
| mara | PERMIT | query_ref, columns, format |
| felix | DENY (Unknown tool: 'export_csv') | - |
| diana | PERMIT | query_ref, columns, format |
| sam | DENY (Unknown tool: 'export_csv') | - |
| anonymous | REJECT (HTTP 401) | - |

### list_data_exports
| User | Decision | Details |
|------|----------|---------|
| mara | PERMIT | [{"export_id":"EXP-001","dataset":"web_traffic","department" |
| felix | PERMIT | [{"export_id":"EXP-001","dataset":"web_traffic","department" |
| diana | PERMIT | [{"export_id":"EXP-001","dataset":"web_traffic","department" |
| sam | PERMIT | [{"export_id":"EXP-001","dataset":"web_traffic","department" |
| anonymous | REJECT (HTTP 401) | - |

### run_model
| User | Decision | Details |
|------|----------|---------|
| mara | DENY (Access denied) | - |
| felix | PERMIT | model_id, dataset, status |
| diana | DENY (Access denied) | - |
| sam | DENY (Access denied) | - |
| anonymous | REJECT (HTTP 401) | - |

### manage_pipelines
| User | Decision | Details |
|------|----------|---------|
| mara | DENY (Access denied) | - |
| felix | PERMIT | operation, pipelines |
| diana | DENY (Access denied) | - |
| sam | DENY (Access denied) | - |
| anonymous | REJECT (HTTP 401) | - |

### purge_dataset
| User | Decision | Details |
|------|----------|---------|
| mara | DENY (Unknown tool: 'purge_dataset') | - |
| felix | DENY (Unknown tool: 'purge_dataset') | - |
| diana | PERMIT | dataset_id, reason, status |
| sam | DENY (Unknown tool: 'purge_dataset') | - |
| anonymous | REJECT (HTTP 401) | - |

## Resource Reads

### data://public/summary
| User | Decision |
|------|----------|
| mara | PERMIT |
| felix | PERMIT |
| diana | PERMIT |
| sam | PERMIT |
| anonymous | REJECT (HTTP 401) |

### data://customers/segments
| User | Decision |
|------|----------|
| mara | PERMIT |
| felix | DENY (Resource not found: data://customers/segments) |
| diana | PERMIT |
| sam | DENY (Resource not found: data://customers/segments) |
| anonymous | REJECT (HTTP 401) |

### data://models/catalog
| User | Decision |
|------|----------|
| mara | DENY (Access denied) |
| felix | PERMIT |
| diana | DENY (Access denied) |
| sam | DENY (Access denied) |
| anonymous | REJECT (HTTP 401) |

### data://audit/log
| User | Decision |
|------|----------|
| mara | DENY (Resource not found: data://audit/log) |
| felix | DENY (Resource not found: data://audit/log) |
| diana | PERMIT |
| sam | DENY (Resource not found: data://audit/log) |
| anonymous | REJECT (HTTP 401) |

### data://models/churn-predictor-v3
| User | Decision |
|------|----------|
| mara | DENY (Access denied) |
| felix | PERMIT |
| diana | DENY (Access denied) |
| sam | DENY (Access denied) |
| anonymous | REJECT (HTTP 401) |

### data://customers/high_value/names
| User | Decision |
|------|----------|
| mara | PERMIT |
| felix | DENY (Resource not found: data://customers/high_value/names) |
| diana | PERMIT |
| sam | DENY (Resource not found: data://customers/high_value/names) |
| anonymous | REJECT (HTTP 401) |

## Prompt Gets

### analyze_trends
| User | Decision |
|------|----------|
| mara | PERMIT |
| felix | PERMIT |
| diana | PERMIT |
| sam | PERMIT |
| anonymous | REJECT (HTTP 401) |

### generate_report
| User | Decision |
|------|----------|
| mara | PERMIT |
| felix | DENY (Access denied) |
| diana | PERMIT |
| sam | DENY (Access denied) |
| anonymous | REJECT (HTTP 401) |

### compliance_review
| User | Decision |
|------|----------|
| mara | DENY (Access denied) |
| felix | DENY (Access denied) |
| diana | PERMIT |
| sam | DENY (Access denied) |
| anonymous | REJECT (HTTP 401) |
