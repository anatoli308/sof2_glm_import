# SoF2 Character Unity Fix - Anleitung

## Problem
Das Problem, das du beschreibst, ist ein häufiges Problem bei der Konvertierung von SoF2-Charakteren für Unity. Der Charakter springt zwischen Edit Mode und Object Mode, was zu inkonsistenter Positionierung führt.

## Ursache
Das Problem entsteht durch:
1. **Inkonsistente Bone-Positionierung**: Root-Bones werden nicht korrekt am Ursprung positioniert
2. **Transformations-Probleme**: Skalierung und Positionierung werden nicht korrekt angewendet
3. **Mode-Switching-Issues**: Blender's Edit/Object Mode verhalten sich unterschiedlich bei der Positionierung

## Lösungen

### 1. Sofortige Lösung - Blender Scripts

Ich habe zwei Scripts erstellt, die du verwenden kannst:

#### `unity_character_fix.py` - Allgemeines Script
```python
# In Blender ausführen:
exec(open("unity_character_fix.py").read())
```

#### `sof2_unity_optimizer.py` - Spezifisch für SoF2
```python
# In Blender ausführen:
exec(open("sof2_unity_optimizer.py").read())
```

### 2. Verbesserte SoF2G2GLA.py

Ich habe deine `SoF2G2GLA.py` verbessert:

#### Änderungen in `MdxaBone.saveToBlender()`:
- Root-Bones werden jetzt korrekt am Ursprung (0,0,0) positioniert
- Verhindert das Springen zwischen Edit und Object Mode

#### Änderungen in `MdxaSkel.saveToBlender()`:
- Armature wird explizit am Ursprung positioniert
- Skalierung wird auf (1,1,1) gesetzt
- Transformationen werden angewendet

### 3. Verwendung der Scripts

#### Schritt 1: Charakter importieren
1. Importiere deinen SoF2-Charakter mit dem verbesserten Addon
2. Der Charakter sollte jetzt korrekt positioniert sein

#### Schritt 2: Script ausführen (falls nötig)
```python
# In Blender's Text Editor oder Python Console:
exec(open("sof2_unity_optimizer.py").read())
```

#### Schritt 3: Für Unity exportieren
```python
# Optional: Direkt zu FBX exportieren
optimizer = SoF2UnityOptimizer()
optimizer.fix_sof2_character(target_scale=1.0, target_location=(0, 0, 0))
optimizer.prepare_for_unity_export("path/to/your/character.fbx")
```

## Was die Scripts machen

### `unity_character_fix.py`
- Findet alle Armaturen und Meshes
- Positioniert sie korrekt am Ursprung
- Wendet Transformationen an
- Bereitet für Unity-Export vor

### `sof2_unity_optimizer.py`
- Spezifisch für SoF2-Charaktere
- Behandelt `skeleton_root` und `scene_root` Objekte
- Erhält die Bone-Hierarchie
- Optimiert für Unity-Export

## Unity-Export Einstellungen

### FBX Export Settings:
- **Scale**: 1.0
- **Apply Unit Scale**: True
- **Apply Scale Options**: FBX_SCALE_NONE
- **Use Space Transform**: True
- **Bake Space Transform**: True
- **Primary Bone Axis**: Y
- **Secondary Bone Axis**: X

## Troubleshooting

### Problem: Charakter springt immer noch
**Lösung**: Führe das Script mehrmals aus oder verwende:
```python
# Alle Transformationen zurücksetzen
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

### Problem: Bones sind falsch positioniert
**Lösung**: Verwende das `sof2_unity_optimizer.py` Script, das die Bone-Hierarchie erhält.

### Problem: Skalierung ist falsch
**Lösung**: Stelle sicher, dass alle Objekte auf Scale (1,1,1) gesetzt sind:
```python
for obj in bpy.context.scene.objects:
    if obj.type in ['ARMATURE', 'MESH']:
        obj.scale = (1, 1, 1)
```

## Zusätzliche Tipps

1. **Cursor Position**: Setze den 3D-Cursor auf (0,0,0) vor dem Import
2. **Origin**: Stelle sicher, dass der Origin aller Objekte am Ursprung ist
3. **Parenting**: Überprüfe die Parent-Child-Beziehungen
4. **Scale**: Alle Objekte sollten auf (1,1,1) skaliert sein

## Kontrolle

Das `sof2_unity_optimizer.py` Script hat eine `check_character_health()` Funktion:
```python
optimizer = SoF2UnityOptimizer()
optimizer.check_character_health()
```

Dies zeigt dir, ob dein Charakter korrekt positioniert ist.

## Fazit

Mit diesen Verbesserungen sollte dein SoF2-Charakter:
- ✅ Konsistent zwischen Edit und Object Mode positioniert sein
- ✅ Korrekt für Unity skaliert sein
- ✅ Am Ursprung (0,0,0) positioniert sein
- ✅ Keine Spring-Probleme mehr haben

Die Scripts sind so konzipiert, dass sie deine bestehenden Charaktere reparieren können, ohne dass du sie neu importieren musst.
