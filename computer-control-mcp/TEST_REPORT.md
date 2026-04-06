# 测试报告：computer-control-mcp

## 摘要

| 项目 | 结果 |
|------|------|
| **执行时间** | 2026-04-06（以本机执行时刻为准） |
| **结论** | **全部通过** |
| **通过 / 失败 / 跳过** | 45 / 0 / 0 |
| **总耗时** | 约 0.54 s |
| **命令** | `pytest tests/ -v --tb=short` |

## 环境

| 项 | 值 |
|----|-----|
| 平台 | darwin |
| Python | 3.13.2 |
| pytest | 9.0.2 |
| pluggy | 1.6.0 |
| pytest-asyncio | 1.3.0 |
| anyio | 4.13.0 |
| 配置 | `pyproject.toml`（`testpaths = tests`，`pythonpath = src`） |
| asyncio 模式 | `auto`，fixture loop scope：`function` |

## 按模块统计

| 测试文件 | 用例数 | 结果 |
|----------|--------|------|
| `tests/test_keymap.py` | 5 | 全部通过 |
| `tests/test_runtime_actions.py` | 22 | 全部通过 |
| `tests/test_runtime_helpers.py` | 13 | 全部通过 |
| `tests/test_server.py` | 7 | 全部通过 |
| **合计** | **45** | **全部通过** |

## 覆盖范围说明

- **键位映射**：组合键、单键、非法键、`super` 相关别名解析。
- **运行时逻辑**：截图缩放、坐标缩放、滚轮刻度换算、十字线绘制、Linux 下截图失败路径（mock）。
- **`handle_computer_sync`**：`key` / `type`（含非 Linux 与 Linux+`xdotool` 分支）、光标查询、鼠标移动、左/右/中键与双击、拖拽、`scroll` 四向及参数错误、`get_screenshot`（含大图下采样）、未知 action、非法 coordinate（mock PyAutoGUI 等）。
- **MCP 服务**：`computer` 工具注册与 schema、`tools/call` 校验与返回形态（JSON / 截图）、未知工具名、`InvalidKeyError` 与普通异常处理（部分用例 mock `handle_computer_sync`）。

## 详细用例列表（均为 PASSED）

### test_keymap.py

1. `test_to_pyautogui_keys_combo`
2. `test_to_pyautogui_keys_single`
3. `test_invalid_key_empty`
4. `test_invalid_key_unknown`
5. `test_super_maps_to_something_valid`

### test_runtime_actions.py

6. `test_key`
7. `test_key_requires_text`
8. `test_type_pyautogui_when_not_linux_xdotool`
9. `test_type_uses_xdotool_on_linux_when_available`
10. `test_get_cursor_position`
11. `test_mouse_move`
12. `test_left_click_with_coordinate`
13. `test_left_click_without_coordinate`
14. `test_left_click_drag`
15. `test_right_click`
16. `test_middle_click`
17. `test_double_click`
18. `test_scroll_directions[up-…]`
19. `test_scroll_directions[down-…]`
20. `test_scroll_directions[left-…]`
21. `test_scroll_directions[right-…]`
22. `test_scroll_default_amount`
23. `test_scroll_errors`
24. `test_get_screenshot`
25. `test_get_screenshot_downscales_large_image`
26. `test_unknown_action`
27. `test_bad_coordinate_length`

### test_runtime_helpers.py

28. `test_get_size_to_api_scale_small_screen`
29. `test_get_size_to_api_scale_long_edge_over_limit`
30. `test_get_api_to_logical_scale`
31. `test_pixels_to_scroll_clicks[0-1]`
32. `test_pixels_to_scroll_clicks[5-1]`
33. `test_pixels_to_scroll_clicks[300-30]`
34. `test_pixels_to_scroll_clicks[100000-500]`
35. `test_scale_coordinate_inside_bounds`
36. `test_scale_coordinate_outside_bounds`
37. `test_draw_crosshair_sets_red_pixel`
38. `test_grab_screen_pil_linux_raises_without_display`

### test_server.py

39. `test_list_tools_registers_computer`
40. `test_call_tool_unknown_name`
41. `test_call_tool_jsonschema_rejects_missing_action`
42. `test_call_tool_json_result`
43. `test_call_tool_screenshot_result`
44. `test_call_tool_invalid_key_error`
45. `test_call_tool_generic_exception`

## 说明与限制

- 当前套件以 **mock** 为主，**不依赖真实显示器或桌面会话**，适合本地与 CI。
- 本报告对应一次在 **macOS (darwin)** 上的执行；在其他 OS 上重新运行 `pytest` 可更新结论。
- 未包含覆盖率（coverage）统计；若需要可在后续增加 `pytest-cov` 并补充一节。

## 复现命令

```bash
cd /path/to/computer-control-mcp
source .venv/bin/activate   # 若使用虚拟环境
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

---

*本报告由测试运行输出整理生成。*
