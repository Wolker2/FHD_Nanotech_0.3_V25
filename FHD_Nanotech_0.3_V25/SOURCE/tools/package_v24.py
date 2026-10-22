"""Package the common V24 core, full editions and a small V23 update."""
import json,shutil
from zipfile import ZipFile,ZIP_DEFLATED
from build_v24 import ROOT,BASES,VARIANTS,COMMON,MODREL
from package_v23 import files,digest

CHANGE='''# Изменения V24

В TEST при создании новой игры один Nanotech уровня 0 автоматически добавляется на личный склад игрока на стартовой планете. Облик выбирает прежний генератор допустимых корпусов. Экипировка игрока не меняется.

Событие BV.OnStart.0DayScripts вооружает скрытую отметку FHDNT_StartGift24. Корпус выдаётся только при наличии отметки в состоянии ожидания. Подтверждение помещения в склад проверяется FindItemInStorage; затем сохраняются состояние «выдан», ID корпуса и планеты. Загрузка сейва, повторное открытие экранов, перенос или продажа подарка не создают новый экземпляр.

Если при инициализации игрок ещё не находится на планете, выдача откладывается до первого подходящего вызова обычного диспетчера. При отказе генератора/склада остаётся ожидающая отметка, не принятый складом предмет освобождается, повторная попытка разрешается через один ход.

В старых сохранениях без этой отметки автоматического подарка нет; остаётся прежняя кнопка «Корпус на склад». RELEASE не вооружает отметку и не выдаёт подарок. Оба режима используют одно ядро.

Это дополнительный тестовый корпус, аналог ручной выдачи. Он не занимает квоту магазинных поставок и не меняет правило обычных поставок по секторам. Таблица XP V23, пороги развития, все рамки/стрелки/кнопки/портреты, механика талантов и совместимость с Червоточиной сохранены.

PASS (static/model): исполнены реальные стартовые и загрузочные строки из Main.dat; проверены один корпус на складе, уровень 0, начало на ходу 61, отсутствие дублей, старые сохранения, задержанная инициализация планеты, отказы генератора и склада, сохранение ожидания через загрузку, отсутствие выдачи в RELEASE, общность ядра и точный состав изменённых файлов. DAT проходит roundtrip прежним проверенным кодеком. В Windows-игре — НЕТ ТЕСТА. Внешний Windows BlockParEditor и srhd_modkit audit/compat здесь не запускались.
'''

def build():
    assert json.loads((COMMON/'validation.json').read_text())['status']=='PASS (static/model)'
    changed={str(MODREL/p)for p in ['CFG/Main.dat','CFG/Rus/Lang.dat','ModuleInfo.txt']}
    mode_differences={str(MODREL/p)for p in ['CFG/Rus/Lang.dat','ModuleInfo.txt']}
    packages=[]
    for edition,out in VARIANTS.items():
        base=BASES[edition]
        mode=('При создании новой игры один Nanotech уровня 0 появляется на личном складе стартовой планеты. Доступны ручной выбор уровня и выдача корпуса.'if edition=='test'else'Обычная прокачка; стартового подарка и тестовых действий нет.')
        (out/'README_RU.md').write_text(f'''# FHD Nanotech 0.3 V24 {edition.upper()}

{mode}

RELEASE и TEST используют одно ядро и одинаковый Main.dat. Различаются только настройки режима в Lang.dat и описание ModuleInfo.txt. Устанавливайте один вариант.

## Установка

Закройте игру. Для полной установки замените Mods/FHD_MODS/FHD_Nanotech целиком папкой из архива. Если установлена Червоточина, включён её прежний файл совместимости Mods/FHD_MODS/FHD_Wormhole/CFG/Main.dat; остальные файлы Червоточины устанавливаются отдельно.

Для установленной V23 достаточно архива V24_PATCH_FOR_V23. Выберите внутри соответствующий режим TEST или RELEASE и скопируйте только его Mods в каталог игры с заменой.

Автоматическая выдача работает только в новой TEST-игре. После начала игры откройте склад стартовой планеты: там будет один Nanotech уровня 0. В текущем сохранении можно воспользоваться прежней кнопкой выдачи корпуса на склад. Подарок не экипируется автоматически и не выдаётся повторно после загрузки, продажи или переноса.

Всё содержимое V23, включая новую шкалу опыта, сохранено. Уровни, опыт, таланты и поставки не сбрасываются. Для отката закройте игру и верните папку V23; уже выданный корпус останется в сохранении. Для точного отката состояния используйте сейв до обновления.

Проверки прошли программно. В Windows-игре V24 ещё не запускалась. Отчёт — reports/validation.json; детали — CHANGELOG.md; прежние награды — FHD_Nanotech_XP_Table_V23_RU.txt.

SOURCE содержит читаемую конфигурацию и инструменты разработки; для повторной сборки нужны прежние рабочие каталоги. Для установки запускать инструменты не требуется.
''',encoding='utf-8')
        (out/'CHANGELOG.md').write_text(CHANGE+'\n'+(base/'CHANGELOG.md').read_text(),encoding='utf-8')
        shutil.copyfile(base/'FHD_Nanotech_XP_Table_V23_RU.txt',out/'FHD_Nanotech_XP_Table_V23_RU.txt')
        shutil.copytree(base/'SOURCE/tools',out/'SOURCE/tools',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        for name in ['build_v24.py','test_v24.py','package_v24.py']:shutil.copyfile(ROOT/'v16_tools'/name,out/'SOURCE/tools'/name)
        shutil.copyfile(base/'reports/validation.json',out/'reports/validation_v23.json')
        (out/'requirements.md').write_text('Цель: один автоматический Nanotech уровня 0 на личном складе при создании новой TEST-игры.\nКритерии: без дублей при загрузке; не выдавать в RELEASE и старых сохранениях; сохранить общее ядро, XP V23, графику, интерфейс и поставки.\n',encoding='utf-8')
        runtime={p.relative_to(out).as_posix():p.read_bytes()for p in files(out/'Mods')}
        previous={p.relative_to(base).as_posix():p.read_bytes()for p in files(base/'Mods')}
        assert runtime.keys()==previous.keys()and len(runtime)==374
        assert {n for n in runtime if runtime[n]!=previous[n]}==changed
        manifest={n:{'bytes':len(b),'sha256':digest(b)}for n,b in runtime.items()}
        (out/'reports/runtime_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
        provenance={'base_version':'V23','base_sha256':digest((ROOT/'deliverables'/f'FHD_Nanotech_0.3_V23_{edition.upper()}_FULL.zip').read_bytes()),'changed_files':sorted(changed),'unchanged_files':len(runtime)-len(changed)}
        (out/'reports/source_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
        path=ROOT/'deliverables'/f'FHD_Nanotech_0.3_V24_{edition.upper()}_FULL.zip'
        with ZipFile(path,'w',ZIP_DEFLATED,compresslevel=6)as z:
            for p in files(out):z.write(p,p.relative_to(out))
        with ZipFile(path)as z:
            assert z.testzip()is None
            names=z.namelist();assert len(names)==len(set(n.lower()for n in names))
            assert all(not n.startswith('/')and '..'not in n.split('/')and '\\'not in n for n in names)
            assert not any(n.lower().endswith(('.exe','.dll','.hai'))for n in names)
            assert all(z.read(n)==b for n,b in runtime.items())
        packages.append({'path':str(path),'edition':edition.upper(),'bytes':path.stat().st_size,'sha256':digest(path.read_bytes()),'runtime_files':len(runtime)})
    patch=ROOT/'deliverables/FHD_Nanotech_0.3_V24_PATCH_FOR_V23.zip'
    with ZipFile(patch,'w',ZIP_DEFLATED,compresslevel=6)as z:
        z.writestr('README_RU.txt','V24 для установленной V23.\n\nЗакройте игру. Выберите внутри TEST или RELEASE согласно установленному режиму. Скопируйте только выбранную папку Mods в каталог игры с заменой.\nВ новой TEST-игре на личный склад стартовой планеты будет выдан один Nanotech уровня 0. Повторной выдачи после загрузки нет. В старых сохранениях используйте прежнюю кнопку выдачи на склад. В RELEASE автоматического подарка нет.\nШкала XP и весь интерфейс сохранены из V23.\nДля отката верните файлы V23. Проверено программно; в Windows-игре пока не проверено.\n')
        z.writestr('CHANGELOG.md',CHANGE)
        for edition,out in VARIANTS.items():
            for n in sorted(changed):z.write(out/n,edition.upper()+'/'+n)
    with ZipFile(patch)as z:
        assert z.testzip()is None
        for edition,out in VARIANTS.items():
            previous={p.relative_to(BASES[edition]).as_posix():p.read_bytes()for p in files(BASES[edition]/'Mods')}
            for n in changed:previous[n]=z.read(edition.upper()+'/'+n)
            assert previous=={p.relative_to(out).as_posix():p.read_bytes()for p in files(out/'Mods')}
    with ZipFile(packages[0]['path'])as a,ZipFile(packages[1]['path'])as b:
        assert {n for n in a.namelist()if n.startswith('Mods/')}=={n for n in b.namelist()if n.startswith('Mods/')}
        assert {n for n in a.namelist()if n.startswith('Mods/')and a.read(n)!=b.read(n)}==mode_differences
    packages.insert(0,{'path':str(patch),'edition':'PATCH_FOR_V23','bytes':patch.stat().st_size,'sha256':digest(patch.read_bytes()),'overlay_matches_full':True})
    (COMMON/'packages.json').write_text(json.dumps(packages,indent=2)+'\n');print(json.dumps(packages))

if __name__=='__main__':build()
