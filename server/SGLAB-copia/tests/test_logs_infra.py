"""Conservación de logs de Docker y acciones, sin tocar servicios reales."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class LogsInfra(unittest.TestCase):
    def test_menu_records_success_and_failure(self):
        for option in [1,2,3,4,5,6,9,10,11]:
            for code in [0,1]:
                with self.subTest(option=option,code=code),tempfile.TemporaryDirectory() as temp:
                    script=f'''
source {shlex.quote(str(ROOT/'infra/infra.sh'))}
DIR_LOGS={shlex.quote(temp)}
levantar_servicios() {{ return {code}; }}
compose() {{ return {code}; }}
exportar_logs() {{ return {code}; }}
reinicializar_bd() {{ return {code}; }}
eliminar_contenedores() {{ return {code}; }}
menu
'''
                    result=subprocess.run(['bash','-c',script],input=f'{option}\n\n0\n',text=True,capture_output=True,env={**os.environ,'TERM':'dumb'})
                    self.assertEqual(result.returncode,0,result.stderr)
                    logs=list(Path(temp).glob('sglab-acciones-*.log'))
                    self.assertEqual(len(logs),1)
                    text=logs[0].read_text()
                    self.assertIn('ERROR' if code else ('WARNING' if option==11 else 'INFO'),text)

    def test_collector_writes_daily_log_and_keeps_other_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);bin_dir=root/'server/bin';bin_dir.mkdir(parents=True)
            script=bin_dir/'logsparadocker.sh';script.write_bytes((ROOT/'server/bin/logsparadocker.sh').read_bytes())
            (root/'compose.yaml').write_text('services: {}\n');(root/'.env').write_text('')
            mock=root/'mock';mock.mkdir()
            docker=mock/'docker';docker.write_text('''#!/bin/sh
case " $* " in
  *" logs "*) printf 'web | mensaje web\\ndb | mensaje db\\n' ;;
esac
exit 0
''');docker.chmod(0o755)
            logs=root/'logs/infra';logs.mkdir(parents=True)
            old=logs/'sglab-docker-2000-01-01.log';old.write_text('viejo')
            preserved=logs/'sglab-acciones-2000-01-01.log';preserved.write_text('acción')
            for path in [old,preserved]:os.utime(path,(time.time()-40*86400,)*2)
            result=subprocess.run(['bash',str(script)],text=True,capture_output=True,env={**os.environ,'PATH':str(mock)+os.pathsep+os.environ['PATH']})
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(old.exists());self.assertTrue(preserved.exists())
            daily=list(logs.glob('sglab-docker-*.log'));self.assertEqual(len(daily),1)
            self.assertIn('mensaje web',daily[0].read_text());self.assertIn('mensaje db',daily[0].read_text())
            self.assertEqual(daily[0].stat().st_mode&0o777,0o600)


if __name__=='__main__':unittest.main()
