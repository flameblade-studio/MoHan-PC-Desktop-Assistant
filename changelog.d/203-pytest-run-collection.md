### pytest 收集 run 測試模組／pytest 收集 run 测试模块／pytest collects run-style test modules／pytest が run 形式のテストモジュールを収集

* pytest 現在會以隔離子行程執行 run 形式的測試，並以防呆測試確保每個測試檔至少收集一項／pytest 现在会以隔离子进程执行 run 形式的测试，并以防护测试确保每个测试文件至少收集一项／pytest now executes run-style tests in isolated child processes and guards that every test file collects at least one item／pytest は run 形式のテストを分離した子プロセスで実行し、各テストファイルから少なくとも一項目が収集されることを防護テストで保証
