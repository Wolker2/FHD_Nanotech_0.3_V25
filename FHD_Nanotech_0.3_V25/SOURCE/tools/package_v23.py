"""Single-process full editions and a two-file-per-mode update from V22."""
import hashlib,json,shutil
from zipfile import ZipFile,ZIP_DEFLATED
from build_v23 import ROOT,BASES,COMMON,VARIANTS,MODREL

def files(root):return [p for p in sorted(root.rglob('*'))if p.is_file()and all(not x.startswith('.')for x in p.relative_to(root).parts)]
def digest(b):return hashlib.sha256(b).hexdigest()

NOTES='''# Изменения V23

База: V22, принятая пользователем как рабочий результат. Добавлено начисление XP по приложенной согласованной таблице от 21.10.2026.

- Доминаторы: Клиг 60, Штип 80, Менок 100, Смерш 150, Ургант 200, Эквентор 250, Бертор 300. Главный Блазер, Келлер и Террон — по 2500.
- Клисаны ShuKlissan: Мутенок 55, Рогит 75, Катаури 95, Нондус 125, Эгемон 170; Махпелла 1500.
- Пираты и военные по рангам 0–7: 55/70/80/100/125/150/200/250.
- Рейнджеры: 45/60/70/90/100/125/150/200.
- Транспорты: 20/30/40/50/60/70/80/90.
- Контрабандисты Smuggler используют пиратскую шкалу и GetShipPirateRank. Пираты также используют GetShipPirateRank; остальные обычные корабли — ShipRank. Профессия рейнджера не меняет его категорию. Дипломаты и лайнеры остаются транспортами.

Пороги развития 0–20 совпадали с таблицей и сохранены. Старый уровень, текущий XP и таланты не обнуляются. Ранее обработанные убийства повторно не начисляются. Награда идёт только экипированному Nanotech-корпусу за подтверждённое событие PlayerKillsShip; убийства напарника/транклюкатора отдельно не добавлены.

## Реализация и ограничения

Штатный журнал не хранит звание: GalaxyEventData(i,5) — подтип корабля; GalaxyEventsTextData(i,2) — ключ изменённого типа. Ранг читается до смерти в t_OnDealingFatalDamage и сохраняется в скрытой инфошке FHDNT_XP23. XP выдаётся после подтверждения убийства журналом через прежнюю защиту от повторов.

Для взрывов есть снимок рангов местной системы раз в ход; непосредственно перед попаданием игрока по предмету t_OnWeaponShot / t_OnMissileHittingObject обновляют метаданные, чтобы учитывать новые корабли и несколько взрывов за ход. Обычные выстрелы по кораблям не запускают сканирование системы. NPC не изменяются; обхода всей Галактики не добавлено. Параметры урона не меняются.

Если сторонний скрипт создаёт событие убийства, обходя все боевые события и снимки живых кораблей, недоступный ранг считается нулевым: восстановить его из стандартного журнала нельзя. Именные награды доминаторов/клисан/Махпеллы от этого не зависят.

Контракт проверен по SpaceRangersHD_decomp, коммит e5317d0c569df57d519e8eb2ef1d8f95b67c12db: aNormalShip.pas ProcessShipKill; aShip.pas ApplyDamage / ApplyExplosionDamage / FireWeaponAtItem; aScriptFun.pas ShipRank, GetShipPirateRank, ScriptItemActionType. Идентификаторы ShuKlissan и ShuSmugglers сверены с исходниками Universe-Original-Mods-Source-main.zip из сохранённых образцов. Чужие игровые скрипты не включались в мод.

PASS (static/model): 108 сценариев наград/рангов в RELEASE и TEST; дополнительно проверены множественные убийства, повторы, загрузка сохранения, обычный корпус, чужой атакующий, взрывы и новые корабли, смена ранга внутри хода, повышение нескольких уровней одной наградой и MAX. DAT проходит roundtrip проверенным для предыдущих сборок кодеком; кириллица сохраняется.

Windows-игра: НЕТ ТЕСТА. Внешний Windows BlockParEditor и srhd_modkit audit/compat в этом окружении не запускались. Подтверждения совместимости со всеми вариантами сторонних модов нет. Проверки не заменяют запуск игры.
'''

def build():
    validation=json.loads((COMMON/'validation.json').read_text());assert validation['status']=='PASS (static/model)'
    changed={str(MODREL/'CFG/Rus/Lang.dat'),str(MODREL/'ModuleInfo.txt')}
    table=(ROOT/'upload/FHD_Nanotech_XP_Table_RU.txt').read_text(encoding='utf-8-sig').split('6. СТАТУС')[0]
    table+='6. СТАТУС\n'+('-'*69)+'\nБаланс внедрён в V23 RELEASE и TEST на одном ядре.\nПроверено программно; в Windows-игре ещё не проверялось.\nПодробности и ограничения — CHANGELOG.md.\n'
    packages=[]
    for edition,out in VARIANTS.items():
        mode='Обычная прокачка опытом. Ручной выбор уровня и выдача корпуса скрыты и отключены.'if edition=='release'else'Тестовый режим: доступны ручной выбор уровня 0–20 и создание корпуса на складе текущей планеты.'
        (out/'README_RU.md').write_text(f'''# FHD Nanotech 0.3 V23 {edition.upper()}

Полная облегчённая сборка с обновлённой таблицей XP. {mode}

RELEASE и TEST используют одно ядро. Различаются только FHDNT.Build / FHDNT.LevelSelection в Lang.dat и описание в ModuleInfo.txt. Устанавливайте один режим.

## Установка и обновление

Закройте игру. Замените Mods/FHD_MODS/FHD_Nanotech целиком папкой из архива. Для ранее установленной Червоточины включён прежний файл совместимости Mods/FHD_MODS/FHD_Wormhole/CFG/Main.dat; остальная Червоточина устанавливается отдельно.

Если уже стоит V22, достаточно маленького патча V23_XP_PATCH_FOR_V22: выберите соответствующую папку RELEASE или TEST и скопируйте её Mods в каталог игры с заменой. Оба режима одновременно не копируйте.

Новая игра не требуется. Уровни, текущий опыт, корпуса, выбранные таланты и квоты поставок сохраняются. Новая шкала применяется к следующим убийствам; перерасчёта старых наград нет. При переходе TEST → RELEASE выданные ранее корпуса и уровни остаются в сохранении.

Точные награды и пороги — FHD_Nanotech_XP_Table_V23_RU.txt. Детали, источники, проверки и ограничения — CHANGELOG.md и reports/validation.json.

Из игрового содержимого V22 изменены только Lang.dat и ModuleInfo.txt. Исправление стрелок V22, рамки, кнопки, таланты, поставки и совместимость с Червоточиной сохранены. Main.dat и 369 графических ресурсов побайтово совпадают с V22. HAI-копии не добавлены; используются анимации оригинальной игры. ShipP сохранена.

Для отката закройте игру и верните папку Nanotech из своей V22. Изменённые после обновления XP/уровни останутся в сохранении; для точного возврата прогресса используйте сохранение, сделанное до обновления.

Проверки: PASS (static/model). В Windows-игре — НЕТ ТЕСТА. Рекомендуемая проверка: загрузить сохранение, уничтожить корабль известного ранга, открыть корпус, проверить прибавку XP, сохранить/загрузить игру и убедиться, что награда не выдана повторно.

SOURCE содержит читаемую конфигурацию и инструменты разработки. Для их повторного запуска нужны прежние рабочие каталоги и образцы. Для установки запускать инструменты не требуется.
''',encoding='utf-8')
        (out/'CHANGELOG.md').write_text(NOTES,encoding='utf-8')
        (out/'FHD_Nanotech_XP_Table_V23_RU.txt').write_text(table,encoding='utf-8-sig')
        (out/'requirements.md').write_text('Цель: обновить награды XP по согласованной таблице, сохранив V22.\nКритерии: ранги 0–7; отдельные доминаторы/клисаны/боссы; однократное начисление; сохранение прогресса; одинаковое ядро режимов; отсутствие изменений интерфейса и графики.\nЗатронутые игровые пути: CFG/Rus/Lang.dat, ModuleInfo.txt.\n',encoding='utf-8')
        shutil.copyfile(BASES[edition]/'SOURCE/CFG/Main.txt',out/'SOURCE/CFG/Main.txt')
        dst=out/'SOURCE/tools';dst.mkdir(parents=True,exist_ok=True)
        for name in ['dat_codec.py','build_hotfix.py','build_v16.py','build_v17.py','build_v18.py','build_v21.py','build_v22.py','build_v23.py','test_hotfix.py','test_v23.py','package_v23.py']:shutil.copyfile(ROOT/'v16_tools'/name,dst/name)
        shutil.copyfile(COMMON/'balance.json',out/'reports/balance.json')
        runtime={p.relative_to(out).as_posix():p.read_bytes()for p in files(out/'Mods')}
        before={p.relative_to(BASES[edition]).as_posix():p.read_bytes()for p in files(BASES[edition]/'Mods')}
        assert runtime.keys()==before.keys() and len(runtime)==374
        assert {n for n in runtime if runtime[n]!=before[n]}==changed
        manifest={n:{'bytes':len(b),'sha256':digest(b)}for n,b in runtime.items()}
        (out/'reports/runtime_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
        provenance={'base_version':'V22','base_archive_sha256':digest((ROOT/'deliverables'/f'FHD_Nanotech_0.3_V22_{edition.upper()}_FULL.zip').read_bytes()),'approved_xp_table_sha256':digest((ROOT/'upload/FHD_Nanotech_XP_Table_RU.txt').read_bytes()),'changed_game_files':sorted(changed),'unchanged_game_files':len(runtime)-len(changed)}
        (out/'reports/source_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
        path=ROOT/'deliverables'/f'FHD_Nanotech_0.3_V23_{edition.upper()}_FULL.zip'
        with ZipFile(path,'w',ZIP_DEFLATED,compresslevel=6)as z:
            for p in files(out):z.write(p,p.relative_to(out))
        with ZipFile(path)as z:
            assert z.testzip()is None
            names=z.namelist();assert len(names)==len(set(n.lower()for n in names))
            assert all(not n.startswith('/')and '..'not in n.split('/')and '\\'not in n for n in names)
            assert not any(n.lower().endswith(('.exe','.dll','.hai'))for n in names)
            assert all(z.read(n)==b for n,b in runtime.items())
        packages.append({'path':str(path),'edition':edition.upper(),'bytes':path.stat().st_size,'sha256':digest(path.read_bytes()),'runtime_files':len(runtime)})
    patch=ROOT/'deliverables/FHD_Nanotech_0.3_V23_XP_PATCH_FOR_V22.zip'
    with ZipFile(patch,'w',ZIP_DEFLATED,compresslevel=6)as z:
        z.writestr('README_RU.txt','V23: новая таблица опыта для установленной V22.\n\nЗакройте игру. Выберите внутри RELEASE или TEST — тот же режим, что установлен у вас. Скопируйте только его папку Mods в каталог игры с заменой файлов. Не копируйте оба режима.\nЗапустите игру и загрузите сохранение. Новая игра не требуется. Старые XP/уровни сохраняются, награды меняются для следующих убийств.\n\nПолные сборки V23 уже содержат этот патч. Откат — возврат файлов V22; для отката прогресса загрузите сохранение до обновления.\nПроверено программно; в Windows-игре ещё не проверялось.\n')
        z.writestr('CHANGELOG.md',NOTES);z.writestr('FHD_Nanotech_XP_Table_V23_RU.txt',b'\xef\xbb\xbf'+table.encode('utf8'))
        for edition,out in VARIANTS.items():
            for n in sorted(changed):z.write(out/n,edition.upper()+'/'+n)
    with ZipFile(patch)as z:
        assert z.testzip()is None
        for edition,out in VARIANTS.items():
            merged={p.relative_to(BASES[edition]).as_posix():p.read_bytes()for p in files(BASES[edition]/'Mods')}
            for n in changed:merged[n]=z.read(edition.upper()+'/'+n)
            assert merged=={p.relative_to(out).as_posix():p.read_bytes()for p in files(out/'Mods')}
    with ZipFile(packages[0]['path'])as a,ZipFile(packages[1]['path'])as b:
        assert {n for n in a.namelist()if n.startswith('Mods/')}=={n for n in b.namelist()if n.startswith('Mods/')}
        assert {n for n in a.namelist()if n.startswith('Mods/')and a.read(n)!=b.read(n)}==changed
    packages.insert(0,{'path':str(patch),'edition':'PATCH_FOR_V22','bytes':patch.stat().st_size,'sha256':digest(patch.read_bytes()),'overlay_matches_full':True})
    (COMMON/'packages.json').write_text(json.dumps(packages,indent=2)+'\n');print(json.dumps(packages))

if __name__=='__main__':build()
