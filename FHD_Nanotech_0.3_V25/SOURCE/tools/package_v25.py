"""Verify and package the V25 shared core and V24 update."""
import json,shutil
from zipfile import ZipFile,ZIP_DEFLATED
from build_v25 import ROOT,BASES,VARIANTS,COMMON,MODREL,MODELS
from package_v23 import files,digest

CHANGE='''# Изменения V25

Из случайного пула исключён малокский рейнджер Maloc_R (ID 16).
Добавлены шесть доминаторских обликов:

| ID | Модель | Серия | Тип |
|---|---|---|---|
| 51 | Blazer3 | Блазероиды | Смерш |
| 52 | Blazer4 | Блазероиды | Менок |
| 53 | Keller3 | Келлероиды | Смерш |
| 54 | Keller4 | Келлероиды | Менок |
| 55 | Terron3 | Терроноиды | Смерш |
| 56 | Terron4 | Терроноиды | Менок |

Теперь доступны 26 обликов. Прежнее случайное развитие 0–20 без повторений сохранено. Нумерация соответствует оригинальному CFG: вариант 3 — Смерш, вариант 4 — Менок.

Анимации полёта и тени подключены через оригинальные Bm.Ship.Blazer3/4, Keller3/4, Terron3/4 и их s-варианты. HAI в мод не копируются. Портреты используют оригинальные Bm.ShipP.2Blazer3/4, 2Keller3/4, 2Terron3/4. Для каждой модели подготовлены маленькие и большие иконки/карточки и GAI-превью магазина: 36 файлов. Превью использует 50 кадров обычной штатной полётной анимации модели; это не новая 360-градусная модель.

Новые облики остаются в серии Nanotech и не становятся серией Червоточина. Малокский рейнджер больше не выбирается случайно. Его прежнее определение и ресурсы сохранены для совместимости уже созданных корпусов; принудительной замены текущего облика в сейве нет. Недопустимый будущий вариант не выбирается при следующем развитии.

Рамки, кнопки, XP V23, таланты, поставки и стартовый TEST-подарок V24 сохранены. RELEASE и TEST имеют одинаковые Main.dat, CacheData.dat, все скрипты и ресурсы; в Lang.dat различаются только два флага режима.

PASS (static/model): 480 переходов развития в обоих режимах, уникальность обликов на уровнях 0–20, появление всех шести новых моделей в случайном выборе, применение каждого нового акрина, корректность путей портретов и полётной графики, декодирование всех кадров 12 GAI, размеры и ненулевая прозрачная графика 24 GI, сброс старого пула и исключение сохранённого Maloc_R из будущего выбора. Изменения Main ограничены шестью новыми Akrin-блоками; прежний интерфейс совпадает побайтово по структуре.

DAT проходит roundtrip прежним кодеком. В Windows-игре — НЕТ ТЕСТА; Windows BlockParEditor и srhd_modkit audit/compat не запускались. Полётная графика сравнивалась с исходным Main.dat, ресурсы — с CacheData.dat и ships.pkg из сохранённого игрового снимка. Контрольные суммы — reports/native_assets.json и reports/source_manifest.json.
'''

def build():
    assert json.loads((COMMON/'validation.json').read_text())['status']=='PASS (static/model)'
    changed={str(MODREL/p)for p in ['CFG/Main.dat','CFG/CacheData.dat','CFG/Rus/Lang.dat','ModuleInfo.txt']}
    mode_diff={str(MODREL/p)for p in ['CFG/Rus/Lang.dat','ModuleInfo.txt']}
    packages=[];patch_files={}
    for edition,out in VARIANTS.items():
        base=BASES[edition]
        (out/'README_RU.md').write_text(f'''# FHD Nanotech 0.3 V25 {edition.upper()}

Из случайного выбора исключён Maloc_R. Добавлены Blazer3/4, Keller3/4 и Terron3/4 — шесть доминаторских обликов. Доступны 26 моделей, развитие 0–20 остаётся случайным и без повторений.

## Установка

Закройте игру. Для полной установки замените Mods/FHD_MODS/FHD_Nanotech целиком папкой из архива. Для установленной Червоточины включён прежний совместимый Mods/FHD_MODS/FHD_Wormhole/CFG/Main.dat; остальные файлы Червоточины устанавливаются отдельно.

Для установленной V24 достаточно маленького архива V25_PATCH_FOR_V24: выберите TEST или RELEASE согласно установленному режиму и скопируйте только его папку Mods в каталог игры с заменой. В патче есть новые изображения: копируйте папку Mods целиком.

Новая игра не требуется. Уровни, опыт и таланты сохраняются. Новый пул используется после полного перезапуска и загрузки игры. Текущий уже установленный Maloc_R насильно не заменяется; он исключён из следующих случайных выборов.

В TEST доступны ручной выбор уровня и выдача корпуса, а в новой игре один Nanotech уровня 0 появляется на личном складе стартовой планеты. В RELEASE эти тестовые действия отключены. Оба режима используют одно ядро.

Полёт подключён к оригинальным анимациям игры, копий HAI нет. Новые магазинные превью основаны на этих же штатных кадрах. Подробности — CHANGELOG.md; внешний вид — PREVIEW/models.png.

Проверено программно. В Windows-игре V25 ещё не запускалась. Проверьте новые модели в TEST выбором уровней, в карточке корпуса, магазине и космосе; затем сохраните и загрузите игру. Отчёт — reports/validation.json.

Откат: при закрытой игре верните полную папку Nanotech V24 и сохранение до обновления, если в новом сейве уже применялся облик 51–56. V24 не содержит их определений.

SOURCE содержит конфигурацию и инструменты. Для повторной сборки нужны прежние рабочие каталоги, оригинальный игровой снимок, NumPy, Pillow и ModKit 0.10.4 из подготовленных инструментов; для установки запускать их не требуется.
''',encoding='utf-8')
        (out/'CHANGELOG.md').write_text(CHANGE+'\n'+(base/'CHANGELOG.md').read_text(),encoding='utf-8')
        shutil.copyfile(base/'FHD_Nanotech_XP_Table_V23_RU.txt',out/'FHD_Nanotech_XP_Table_V23_RU.txt')
        shutil.copytree(base/'SOURCE/tools',out/'SOURCE/tools',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        for name in ['build_v25.py','test_v25.py','package_v25.py']:shutil.copyfile(ROOT/'v16_tools'/name,out/'SOURCE/tools'/name)
        shutil.copyfile(base/'reports/validation.json',out/'reports/validation_v24.json')
        shutil.copyfile(COMMON/'native_assets.json',out/'reports/native_assets.json')
        (out/'PREVIEW').mkdir(exist_ok=True);shutil.copyfile(COMMON/'models_preview.png',out/'PREVIEW/models.png')
        (out/'requirements.md').write_text('Исключить Maloc_R; добавить штатные модели 3/4 серий Blazer, Keller, Terron. Сохранить выбор без повторений на уровнях 0–20, оригинальные ссылки на полёт, общее ядро RELEASE/TEST и весь рабочий интерфейс.\n',encoding='utf-8')
        runtime={p.relative_to(out).as_posix():p.read_bytes()for p in files(out/'Mods')}
        old={p.relative_to(base).as_posix():p.read_bytes()for p in files(base/'Mods')}
        assert old.keys()<=runtime.keys()and len(runtime)==410
        assert {n for n in old if old[n]!=runtime[n]}==changed
        added=runtime.keys()-old.keys();assert len(added)==36 and all('/DominatorPreview/'in n for n in added)
        patch_files[edition]=changed|added
        manifest={n:{'bytes':len(b),'sha256':digest(b)}for n,b in runtime.items()}
        (out/'reports/runtime_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
        provenance={'base_version':'V24','base_sha256':digest((ROOT/'deliverables'/f'FHD_Nanotech_0.3_V24_{edition.upper()}_FULL.zip').read_bytes()),'changed_files':sorted(changed),'new_files':sorted(added),'copied_hai_files':0}
        (out/'reports/source_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
        path=ROOT/'deliverables'/f'FHD_Nanotech_0.3_V25_{edition.upper()}_FULL.zip'
        with ZipFile(path,'w',ZIP_DEFLATED,compresslevel=6)as z:
            for p in files(out):z.write(p,p.relative_to(out))
        with ZipFile(path)as z:
            assert z.testzip()is None
            names=z.namelist();assert len(names)==len(set(n.lower()for n in names))
            assert all(not n.startswith('/')and '..'not in n.split('/')and '\\'not in n for n in names)
            assert not any(n.lower().endswith(('.exe','.dll','.hai'))for n in names)
            assert all(z.read(n)==b for n,b in runtime.items())
        packages.append({'path':str(path),'edition':edition.upper(),'bytes':path.stat().st_size,'sha256':digest(path.read_bytes()),'runtime_files':len(runtime)})
    patch=ROOT/'deliverables/FHD_Nanotech_0.3_V25_PATCH_FOR_V24.zip'
    with ZipFile(patch,'w',ZIP_DEFLATED,compresslevel=6)as z:
        z.writestr('README_RU.txt','V25 для установленной V24.\n\nЗакройте игру. Выберите внутри TEST или RELEASE согласно установленному режиму. Скопируйте только его папку Mods целиком в каталог игры с заменой, включая DATA с новыми превью.\nMaloc_R исключён, добавлены Blazer3/4, Keller3/4, Terron3/4. Всего 26 обликов, развитие 0–20 без повторений. Новая игра не нужна.\nУже установленный Maloc_R насильно не заменяется; он не выпадает при следующих выборах. Уровни, опыт, таланты, рамки и кнопки сохранены.\nПроверено программно; в Windows-игре пока не проверено. Откат — полная папка V24 и старый сейв, если уже применялись новые облики 51–56.\n')
        z.writestr('CHANGELOG.md',CHANGE)
        for edition,out in VARIANTS.items():
            for n in sorted(patch_files[edition]):z.write(out/n,edition.upper()+'/'+n)
    with ZipFile(patch)as z:
        assert z.testzip()is None
        for edition,out in VARIANTS.items():
            old={p.relative_to(BASES[edition]).as_posix():p.read_bytes()for p in files(BASES[edition]/'Mods')}
            for n in patch_files[edition]:old[n]=z.read(edition.upper()+'/'+n)
            assert old=={p.relative_to(out).as_posix():p.read_bytes()for p in files(out/'Mods')}
    with ZipFile(packages[0]['path'])as a,ZipFile(packages[1]['path'])as b:
        assert {n for n in a.namelist()if n.startswith('Mods/')}=={n for n in b.namelist()if n.startswith('Mods/')}
        assert {n for n in a.namelist()if n.startswith('Mods/')and a.read(n)!=b.read(n)}==mode_diff
    packages.insert(0,{'path':str(patch),'edition':'PATCH_FOR_V24','bytes':patch.stat().st_size,'sha256':digest(patch.read_bytes()),'overlay_matches_full':True})
    (COMMON/'packages.json').write_text(json.dumps(packages,indent=2)+'\n');print(json.dumps(packages))

if __name__=='__main__':build()
