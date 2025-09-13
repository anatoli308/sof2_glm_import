Ich erstelle eine umfassende Zusammenfassung aller Dokumentationen für Sie. Lassen Sie mich zuerst die verfügbaren Dokumente analysieren.


[6 tools called]

Basierend auf den verfügbaren Informationen aus den beiden lesbaren Dokumenten erstelle ich Ihnen eine umfassende Zusammenfassung:

# BESSERE_ZUSAMMENFASSUNG.md

## Soldier of Fortune 2 (SoF2) Modding & Unity Porting Guide

### Inhaltsverzeichnis
1. [Character System Overview](#character-system-overview)
2. [NPC Template System](#npc-template-system)
3. [Skinning System](#skinning-system)
4. [Shader System](#shader-system)
5. [Weapon System](#weapon-system)
6. [Unity Porting Strategy](#unity-porting-strategy)
7. [Code Examples & Implementation](#code-examples--implementation)

---

## Character System Overview

### Grundlegende Architektur
SoF2 verwendet ein modulares Character-System mit folgenden Komponenten:

- **GLM Models**: Ghoul2 Model Format für 3D-Modelle
- **G2Skin Files**: Skin-Definitionen mit Material-Zuweisungen
- **NPC Templates**: Character-Konfigurationen mit Vererbung
- **Shader System**: Quake3-basierte Shader für Texturen
- **Animation System**: GLA-Dateien für Animationen

### Verzeichnisstruktur
```
base/
├── models/characters/
│   ├── average_sleeves/          # Basis-Character Model
│   ├── skins/                    # .g2skin Dateien
│   └── [character_name]/         # Spezifische Character
├── npcs/                         # .npc Template Dateien
├── shaders/                      # .shader Dateien
└── ext_data/
    ├── sof2.item                 # Item-Definitionen
    └── sof2.wpn                  # Waffen-Definitionen
```

---

## NPC Template System

### Template-Vererbung
Das NPC-System verwendet ein hierarchisches Vererbungssystem:

```json
{
  "GroupInfo": {
    "Skeleton": "average_sleeves.skl",
    "ParentTemplate": "NPC_Base_Human"
  },
  "CharacterTemplate": {
    "Name": "NPC_Marine_Soldier",
    "Team": "The Shop",
    "Rank": "Private",
    "Occupation": "Soldier",
    "Accuracy": "0.7",
    "Inventory": {
      "Weapons": [
        {
          "Name": "US SOCOM",
          "Bolt": "*hip_r",
          "Chance": 100
        }
      ],
      "Items": [
        {
          "Name": "ammo_pack_green",
          "Bolt": "*hip_fl",
          "Chance": 100
        }
      ]
    },
    "Skin": {
      "File": "marine_camo2",
      "Inventory": {
        "Weapons": [
          {
            "Name": "M4"
          }
        ],
        "Items": [
          {
            "Name": "backpack",
            "mp_onback": true
          }
        ]
      }
    }
  }
}
```

### Berufe und Ränge
**Ränge:**
- `Civilian` - Zivilisten
- `Criminal` - Kriminelle
- `Private` - Soldaten (häufigster Rang)
- `Sergeant` - Unteroffiziere

**Berufe:**
- `Soldier` - Standard-Soldat
- `Assassin` - Attentäter (vorsichtiger)
- `Commando` - Kommando (arbeitet in Paaren)
- `Demolitionist` - Sprengstoffexperte
- `Sniper` - Scharfschütze
- `Scout` - Aufklärer
- `Emplaced Gunner` - Geschützbediener

### Inventar-System
- **Global Inventory**: Wird an alle Charaktere vererbt
- **Skin Inventory**: Nur bei spezifischen Skins aktiv
- **Bolt Points**: Befestigungspunkte für Items (`*hip_r`, `*head_t`, etc.)

---

## Skinning System

### ModView Workflow
1. **Model Loading**: `.mvs` Scripts laden
2. **Surface Management**: Verschiedene Oberflächen ein/ausschalten
3. **Skin Application**: `.g2skin` Dateien anwenden
4. **Validation**: Shader-Validierung

### G2Skin Dateiformat
```json
{
  "prefs": {
    "models": [
      "average_sleeves",
      "average_sleeves_mini"
    ]
  },
  "materials": [
    {
      "name": "face",
      "groups": [
        {
          "name": "white",
          "texture1": "models/characters/average_face/f_marine_camo2"
        }
      ]
    },
    {
      "name": "body",
      "groups": [
        {
          "name": "white",
          "texture1": "models/characters/average_sleeves/b_marine_camo2"
        }
      ]
    }
  ]
}
```

### Erforderliche Materialien
**Pflicht:**
- `face` - Gesicht
- `body` - Körper
- `arms` - Arme
- `caps` - Kopfbedeckung
- `face_2sided` - Zähne
- `head` / `avmed` / `avmedhat` - Haartyp

**Optional:**
- `body_2sided` - Kragen
- `scarf` - Schal
- `backpack_lrg` - Rucksack
- `helmet_chin_strap` - Helmriemen
- `avmst` - Schnurrbart

### Surface System
- **Hair Styles**: `avmed` (mittel), `head` (kahl), `avmedhat` (rund)
- **Equipment**: `backpack`, `scarf`, `helmet_chin_strap`
- **Tags**: `*head_t`, `*hip_r` (Befestigungspunkte)

---

## Shader System

### Standard Shader
```shader
models/characters/average_sleeves/scarf
{
    {
        map models/characters/average_sleeves/scarf_marine
        rgbGen lightingDiffuse
    }
}
```

### 2-Sided Shader
```shader
models/characters/average_sleeves/b2_marine_camo2
{
    cull    disable
    {
        map models/characters/average_sleeves/b_marine_camo2
        rgbGen lightingDiffuse
    }
}
```

### Shader Parameter
- `rgbGen lightingDiffuse` - Beleuchtungsberechnung
- `cull disable` - Beidseitige Darstellung
- `map` - Texturpfad

---

## Weapon System

### Waffen-Komponenten
1. **SOF2.item** - Item-Definitionen
2. **SOF2.wpn** - Waffen-Eigenschaften
3. **Frames File** - Animations-Frames
4. **Inview File** - Sicht-Modell
5. **Overview** - Waffen-Übersicht

### Item Definition (SOF2.item)
```json
{
  "weapons": [
    {
      "name": "US SOCOM",
      "type": "pistol",
      "damage": 25,
      "range": 1000,
      "ammo_type": "9mm",
      "bolt_points": ["*hip_r", "*hand_r"]
    }
  ],
  "items": [
    {
      "name": "ammo_pack_green",
      "type": "ammo",
      "ammo_type": "9mm",
      "amount": 30,
      "bolt_points": ["*hip_fl", "*uchest_l"]
    }
  ]
}
```

### Waffen-Properties (SOF2.wpn)
```json
{
  "weapon_properties": [
    {
      "name": "US SOCOM",
      "fire_rate": 0.2,
      "reload_time": 2.0,
      "accuracy": 0.8,
      "recoil": 0.3,
      "sounds": {
        "fire": "weapons/socom_fire.wav",
        "reload": "weapons/socom_reload.wav"
      }
    }
  ]
}
```

---

## Unity Porting Strategy

### 1. Asset Pipeline Setup

#### Blender → Unity Workflow
```python
# Blender Export Script für Unity
import bpy
import json

def export_character_for_unity():
    # Model Export
    bpy.ops.export_scene.fbx(
        filepath="Assets/Characters/character.fbx",
        use_selection=False,
        use_mesh_modifiers=True,
        use_armature_deform_only=True
    )
    
    # Animation Export
    for action in bpy.data.actions:
        bpy.context.object.animation_data.action = action
        bpy.ops.export_scene.fbx(
            filepath=f"Assets/Animations/{action.name}.fbx",
            use_selection=True,
            use_armature_deform_only=True
        )

def create_character_config():
    config = {
        "character_name": "Marine_Soldier",
        "prefab_path": "Characters/Marine_Soldier",
        "materials": {
            "face": "Materials/face_marine",
            "body": "Materials/body_marine",
            "arms": "Materials/arms_marine"
        },
        "inventory": {
            "weapons": ["US_SOCOM", "M4"],
            "items": ["ammo_pack_green", "backpack"]
        },
        "bolt_points": {
            "hip_r": "Bip01_R_Thigh",
            "hip_fl": "Bip01_L_Thigh",
            "head_t": "Bip01_Head"
        }
    }
    
    with open("Assets/Characters/Marine_Soldier.json", "w") as f:
        json.dump(config, f, indent=2)
```

### 2. Unity Scripts

#### Character Template System
```csharp
using UnityEngine;
using System.Collections.Generic;

[System.Serializable]
public class CharacterTemplate
{
    public string name;
    public string team;
    public string rank;
    public string occupation;
    public float accuracy;
    public InventoryData inventory;
    public SkinData skin;
}

[System.Serializable]
public class InventoryData
{
    public List<WeaponData> weapons;
    public List<ItemData> items;
}

[System.Serializable]
public class WeaponData
{
    public string name;
    public string boltPoint;
    public int chance = 100;
}

[System.Serializable]
public class ItemData
{
    public string name;
    public string boltPoint;
    public bool mpOnBack = false;
    public int chance = 100;
}

[System.Serializable]
public class SkinData
{
    public string file;
    public InventoryData inventory;
}

public class CharacterManager : MonoBehaviour
{
    [SerializeField] private CharacterTemplate characterTemplate;
    [SerializeField] private Transform boltPoints;
    [SerializeField] private SkinnedMeshRenderer characterRenderer;
    
    private Dictionary<string, Transform> boltPointMap;
    
    void Start()
    {
        LoadCharacterTemplate();
        SetupBoltPoints();
        ApplyInventory();
    }
    
    void LoadCharacterTemplate()
    {
        string jsonPath = $"Characters/{characterTemplate.name}";
        TextAsset jsonFile = Resources.Load<TextAsset>(jsonPath);
        
        if (jsonFile != null)
        {
            characterTemplate = JsonUtility.FromJson<CharacterTemplate>(jsonFile.text);
        }
    }
    
    void SetupBoltPoints()
    {
        boltPointMap = new Dictionary<string, Transform>();
        
        foreach (Transform child in boltPoints)
        {
            boltPointMap[child.name] = child;
        }
    }
    
    void ApplyInventory()
    {
        // Apply global inventory
        foreach (var weapon in characterTemplate.inventory.weapons)
        {
            if (Random.Range(0, 100) < weapon.chance)
            {
                AttachWeapon(weapon);
            }
        }
        
        // Apply skin-specific inventory
        if (characterTemplate.skin != null)
        {
            foreach (var weapon in characterTemplate.skin.inventory.weapons)
            {
                AttachWeapon(weapon);
            }
        }
    }
    
    void AttachWeapon(WeaponData weaponData)
    {
        if (boltPointMap.ContainsKey(weaponData.boltPoint))
        {
            GameObject weaponPrefab = Resources.Load<GameObject>($"Weapons/{weaponData.name}");
            if (weaponPrefab != null)
            {
                GameObject weapon = Instantiate(weaponPrefab, boltPointMap[weaponData.boltPoint]);
                weapon.transform.localPosition = Vector3.zero;
                weapon.transform.localRotation = Quaternion.identity;
            }
        }
    }
}
```

#### Material System
```csharp
using UnityEngine;

[System.Serializable]
public class MaterialData
{
    public string name;
    public string texturePath;
    public bool twoSided = false;
}

public class MaterialManager : MonoBehaviour
{
    [SerializeField] private MaterialData[] materials;
    [SerializeField] private SkinnedMeshRenderer characterRenderer;
    
    void Start()
    {
        ApplyMaterials();
    }
    
    void ApplyMaterials()
    {
        Material[] characterMaterials = new Material[materials.Length];
        
        for (int i = 0; i < materials.Length; i++)
        {
            MaterialData matData = materials[i];
            Material material = new Material(Shader.Find("Standard"));
            
            // Load texture
            Texture2D texture = Resources.Load<Texture2D>(matData.texturePath);
            if (texture != null)
            {
                material.mainTexture = texture;
            }
            
            // Set two-sided rendering
            if (matData.twoSided)
            {
                material.SetInt("_Cull", 0); // No culling
            }
            
            characterMaterials[i] = material;
        }
        
        characterRenderer.materials = characterMaterials;
    }
}
```

#### Weapon System
```csharp
using UnityEngine;

[System.Serializable]
public class WeaponProperties
{
    public string name;
    public float fireRate;
    public float reloadTime;
    public float accuracy;
    public float recoil;
    public AudioClip fireSound;
    public AudioClip reloadSound;
}

public class WeaponController : MonoBehaviour
{
    [SerializeField] private WeaponProperties weaponProps;
    [SerializeField] private Transform firePoint;
    [SerializeField] private AudioSource audioSource;
    
    private float lastFireTime;
    private bool isReloading = false;
    
    void Update()
    {
        if (Input.GetButton("Fire1") && CanFire())
        {
            Fire();
        }
        
        if (Input.GetKeyDown(KeyCode.R) && !isReloading)
        {
            StartCoroutine(Reload());
        }
    }
    
    bool CanFire()
    {
        return Time.time - lastFireTime >= weaponProps.fireRate && !isReloading;
    }
    
    void Fire()
    {
        lastFireTime = Time.time;
        
        // Play fire sound
        if (weaponProps.fireSound != null)
        {
            audioSource.PlayOneShot(weaponProps.fireSound);
        }
        
        // Apply recoil
        ApplyRecoil();
        
        // Raycast for hit detection
        RaycastHit hit;
        if (Physics.Raycast(firePoint.position, firePoint.forward, out hit))
        {
            // Handle hit
            Debug.Log($"Hit: {hit.collider.name}");
        }
    }
    
    void ApplyRecoil()
    {
        float recoilAmount = weaponProps.recoil * Random.Range(0.8f, 1.2f);
        transform.Rotate(-recoilAmount, Random.Range(-recoilAmount/2, recoilAmount/2), 0);
    }
    
    System.Collections.IEnumerator Reload()
    {
        isReloading = true;
        
        if (weaponProps.reloadSound != null)
        {
            audioSource.PlayOneShot(weaponProps.reloadSound);
        }
        
        yield return new WaitForSeconds(weaponProps.reloadTime);
        isReloading = false;
    }
}
```

### 3. Unity Asset Structure

```
Assets/
├── Characters/
│   ├── Prefabs/
│   │   ├── Marine_Soldier.prefab
│   │   └── Colombian_Rebel.prefab
│   ├── Materials/
│   │   ├── face_marine.mat
│   │   ├── body_marine.mat
│   │   └── arms_marine.mat
│   ├── Textures/
│   │   ├── face_marine.png
│   │   ├── body_marine.png
│   │   └── arms_marine.png
│   └── Configs/
│       ├── Marine_Soldier.json
│       └── Colombian_Rebel.json
├── Weapons/
│   ├── Prefabs/
│   │   ├── US_SOCOM.prefab
│   │   └── M4.prefab
│   ├── Models/
│   │   ├── US_SOCOM.fbx
│   │   └── M4.fbx
│   └── Configs/
│       ├── US_SOCOM.json
│       └── M4.json
├── Animations/
│   ├── idle.fbx
│   ├── walk.fbx
│   ├── run.fbx
│   └── fire.fbx
└── Scripts/
    ├── CharacterManager.cs
    ├── MaterialManager.cs
    └── WeaponController.cs
```

### 4. Migration Checklist

#### Phase 1: Asset Preparation
- [ ] Blender Models zu FBX exportieren
- [ ] Animationen einzeln exportieren
- [ ] Texturen optimieren (Power of 2, komprimiert)
- [ ] Material-Shader anpassen

#### Phase 2: Unity Setup
- [ ] Character Prefabs erstellen
- [ ] Material-System implementieren
- [ ] Bolt-Point System einrichten
- [ ] Animation Controller setup

#### Phase 3: Systems Implementation
- [ ] Character Template System
- [ ] Inventory System
- [ ] Weapon System
- [ ] AI Behavior (falls benötigt)

#### Phase 4: Optimization
- [ ] LOD System für Characters
- [ ] Texture Atlasing
- [ ] Animation Compression
- [ ] Memory Profiling

### 5. Performance Considerations

```csharp
// Object Pooling für Waffen
public class WeaponPool : MonoBehaviour
{
    [SerializeField] private GameObject weaponPrefab;
    [SerializeField] private int poolSize = 10;
    
    private Queue<GameObject> weaponPool;
    
    void Start()
    {
        weaponPool = new Queue<GameObject>();
        
        for (int i = 0; i < poolSize; i++)
        {
            GameObject weapon = Instantiate(weaponPrefab);
            weapon.SetActive(false);
            weaponPool.Enqueue(weapon);
        }
    }
    
    public GameObject GetWeapon()
    {
        if (weaponPool.Count > 0)
        {
            GameObject weapon = weaponPool.Dequeue();
            weapon.SetActive(true);
            return weapon;
        }
        
        return Instantiate(weaponPrefab);
    }
    
    public void ReturnWeapon(GameObject weapon)
    {
        weapon.SetActive(false);
        weaponPool.Enqueue(weapon);
    }
}
```

---

---

## Animation System (ROF Format)

### ROFF (Raven Object File Format)
SoF2 verwendet ein proprietäres Animationsformat für Weltobjekte:

#### Workflow für animierte Objekte
1. **Radiant Setup**: Objekt als `func_wall` erstellen
2. **Map Export**: Objekt in neue Map kopieren
3. **BSP Compilation**: `sof2map -lwo -max map.bsp`
4. **3DS Max Import**: `.lwo` Datei importieren
5. **Animation**: Objekt animieren
6. **Export**: Als `.rof` Datei exportieren

#### 3DS Max Konfiguration
```maxscript
-- Max Setup für SoF2 Animation
-- System Unit Scale: 1 Unit = 6.0 Inches
-- Grid Spacing: 8.0
-- Frame Rate: 20 FPS
-- Scale Factor: 15.24 (automatisch mit -max flag)
```

#### ROFF Export Script
```maxscript
-- Export Selected Objects as ROF
fn exportROF objName =
(
    local rofPath = "base/maps/" + objName + ".rof"
    exportFile rofPath #noPrompt selectedOnly:true
)
```

#### ICARUS Scripting Integration
```c
// ICARUS Script für animierte Objekte
affect ( "animated_object", FLUSH )
{
    use ( "maps/boom.rof" );
    wait ( 2000.000 );
    kill ( "animated_object" );
}
```

---

## Erweiterte Unity Porting Features

### 6. Animation System Migration

#### ROFF zu Unity Animation Converter
```csharp
using UnityEngine;
using System.Collections.Generic;

[System.Serializable]
public class ROFFAnimationData
{
    public string objectName;
    public AnimationClip[] clips;
    public float frameRate = 20f;
    public Vector3 origin;
}

public class ROFFImporter : MonoBehaviour
{
    [SerializeField] private ROFFAnimationData roffData;
    [SerializeField] private Animator animator;
    
    void Start()
    {
        ConvertROFFToUnity();
    }
    
    void ConvertROFFToUnity()
    {
        // Convert 20 FPS to Unity's 60 FPS
        foreach (var clip in roffData.clips)
        {
            clip.frameRate = 60f;
            
            // Scale animation keys for Unity units
            ScaleAnimationKeys(clip);
        }
        
        // Apply to Animator Controller
        RuntimeAnimatorController controller = animator.runtimeAnimatorController;
        AnimatorController ac = controller as AnimatorController;
        
        foreach (var clip in roffData.clips)
        {
            ac.AddMotion(clip);
        }
    }
    
    void ScaleAnimationKeys(AnimationClip clip)
    {
        // Scale from SoF2 units to Unity units
        float scaleFactor = 0.0328f; // SoF2 to Unity conversion
        
        foreach (var binding in AnimationUtility.GetCurveBindings(clip))
        {
            AnimationCurve curve = AnimationUtility.GetEditorCurve(clip, binding);
            
            for (int i = 0; i < curve.keys.Length; i++)
            {
                Keyframe key = curve.keys[i];
                key.value *= scaleFactor;
                curve.MoveKey(i, key);
            }
            
            AnimationUtility.SetEditorCurve(clip, binding, curve);
        }
    }
}
```

### 7. Advanced Material System

#### Shader Graph Implementation
```hlsl
// Custom SoF2 Shader für Unity Shader Graph
Shader "SoF2/CharacterShader"
{
    Properties
    {
        _MainTex ("Base Texture", 2D) = "white" {}
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _Specular ("Specular", Range(0,1)) = 0.5
        _TwoSided ("Two Sided", Float) = 0
    }
    
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        LOD 200
        
        Cull [_TwoSided]
        
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        
        sampler2D _MainTex;
        sampler2D _NormalMap;
        float _Specular;
        
        struct Input
        {
            float2 uv_MainTex;
            float2 uv_NormalMap;
        };
        
        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex);
            o.Albedo = c.rgb;
            o.Normal = UnpackNormal(tex2D(_NormalMap, IN.uv_NormalMap));
            o.Specular = _Specular;
            o.Alpha = c.a;
        }
        ENDCG
    }
}
```

### 8. Performance Optimization System

#### LOD System für Characters
```csharp
using UnityEngine;

public class CharacterLODSystem : MonoBehaviour
{
    [System.Serializable]
    public class LODLevel
    {
        public float distance;
        public int meshQuality;
        public bool enableShadows;
        public bool enableAnimations;
    }
    
    [SerializeField] private LODLevel[] lodLevels;
    [SerializeField] private SkinnedMeshRenderer[] lodRenderers;
    [SerializeField] private Animator animator;
    [SerializeField] private Transform player;
    
    private int currentLOD = 0;
    
    void Update()
    {
        float distance = Vector3.Distance(transform.position, player.position);
        int newLOD = GetLODLevel(distance);
        
        if (newLOD != currentLOD)
        {
            SetLODLevel(newLOD);
        }
    }
    
    int GetLODLevel(float distance)
    {
        for (int i = lodLevels.Length - 1; i >= 0; i--)
        {
            if (distance <= lodLevels[i].distance)
                return i;
        }
        return lodLevels.Length - 1;
    }
    
    void SetLODLevel(int lodLevel)
    {
        currentLOD = lodLevel;
        LODLevel level = lodLevels[lodLevel];
        
        // Enable/disable renderers
        for (int i = 0; i < lodRenderers.Length; i++)
        {
            lodRenderers[i].enabled = (i == lodLevel);
        }
        
        // Configure quality settings
        if (lodRenderers[lodLevel] != null)
        {
            lodRenderers[lodLevel].shadowCastingMode = 
                level.enableShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
        }
        
        // Animation quality
        animator.enabled = level.enableAnimations;
    }
}
```

### 9. Advanced Inventory System

#### Dynamic Equipment System
```csharp
using UnityEngine;
using System.Collections.Generic;

[System.Serializable]
public class EquipmentSlot
{
    public string slotName;
    public Transform attachPoint;
    public GameObject currentItem;
    public List<string> allowedItems;
}

public class AdvancedInventorySystem : MonoBehaviour
{
    [SerializeField] private EquipmentSlot[] equipmentSlots;
    [SerializeField] private Dictionary<string, EquipmentSlot> slotMap;
    
    void Start()
    {
        InitializeSlotMap();
    }
    
    void InitializeSlotMap()
    {
        slotMap = new Dictionary<string, EquipmentSlot>();
        foreach (var slot in equipmentSlots)
        {
            slotMap[slot.slotName] = slot;
        }
    }
    
    public bool EquipItem(string itemName, string slotName)
    {
        if (!slotMap.ContainsKey(slotName)) return false;
        
        EquipmentSlot slot = slotMap[slotName];
        
        // Check if item is allowed in this slot
        if (!slot.allowedItems.Contains(itemName)) return false;
        
        // Unequip current item
        if (slot.currentItem != null)
        {
            UnequipItem(slotName);
        }
        
        // Equip new item
        GameObject itemPrefab = Resources.Load<GameObject>($"Items/{itemName}");
        if (itemPrefab != null)
        {
            GameObject item = Instantiate(itemPrefab, slot.attachPoint);
            item.transform.localPosition = Vector3.zero;
            item.transform.localRotation = Quaternion.identity;
            
            slot.currentItem = item;
            return true;
        }
        
        return false;
    }
    
    public void UnequipItem(string slotName)
    {
        if (!slotMap.ContainsKey(slotName)) return;
        
        EquipmentSlot slot = slotMap[slotName];
        if (slot.currentItem != null)
        {
            Destroy(slot.currentItem);
            slot.currentItem = null;
        }
    }
}
```

### 10. AI Behavior System

#### SoF2 AI zu Unity Behavior Tree
```csharp
using UnityEngine;
using System.Collections;

public class SoF2AIBehavior : MonoBehaviour
{
    [System.Serializable]
    public class AIState
    {
        public string stateName;
        public float patrolRadius;
        public float reactionTime;
        public bool canUseCover;
        public bool canThrowGrenades;
    }
    
    [SerializeField] private AIState[] aiStates;
    [SerializeField] private string currentOccupation;
    [SerializeField] private Transform[] patrolPoints;
    [SerializeField] private LayerMask coverLayer;
    
    private AIState currentState;
    private int currentPatrolIndex = 0;
    private bool isAlerted = false;
    
    void Start()
    {
        SetOccupation(currentOccupation);
    }
    
    void SetOccupation(string occupation)
    {
        // Map SoF2 occupations to Unity AI states
        switch (occupation.ToLower())
        {
            case "soldier":
                currentState = GetStateByName("Patrol");
                break;
            case "assassin":
                currentState = GetStateByName("Stealth");
                break;
            case "commando":
                currentState = GetStateByName("Tactical");
                break;
            case "sniper":
                currentState = GetStateByName("LongRange");
                break;
            default:
                currentState = GetStateByName("Patrol");
                break;
        }
    }
    
    AIState GetStateByName(string name)
    {
        foreach (var state in aiStates)
        {
            if (state.stateName == name)
                return state;
        }
        return aiStates[0];
    }
    
    void Update()
    {
        if (isAlerted)
        {
            HandleCombat();
        }
        else
        {
            HandlePatrol();
        }
    }
    
    void HandlePatrol()
    {
        if (patrolPoints.Length == 0) return;
        
        Transform target = patrolPoints[currentPatrolIndex];
        float distance = Vector3.Distance(transform.position, target.position);
        
        if (distance < 1f)
        {
            currentPatrolIndex = (currentPatrolIndex + 1) % patrolPoints.Length;
        }
        else
        {
            MoveToTarget(target.position);
        }
    }
    
    void HandleCombat()
    {
        // Implement combat behavior based on occupation
        if (currentState.canUseCover)
        {
            FindCover();
        }
        
        if (currentState.canThrowGrenades)
        {
            // Implement grenade throwing logic
        }
    }
    
    void MoveToTarget(Vector3 target)
    {
        // Basic movement implementation
        Vector3 direction = (target - transform.position).normalized;
        transform.position += direction * Time.deltaTime * 2f;
        transform.LookAt(target);
    }
    
    void FindCover()
    {
        // Raycast to find cover points
        RaycastHit hit;
        if (Physics.Raycast(transform.position, transform.forward, out hit, 5f, coverLayer))
        {
            // Move to cover position
            MoveToTarget(hit.point);
        }
    }
}
```

---

## Erweiterte Migration Checklist

### Phase 5: Advanced Features
- [ ] ROFF Animation System implementieren
- [ ] Custom Shader Graph erstellen
- [ ] LOD System für Performance
- [ ] Advanced Inventory System
- [ ] AI Behavior Trees
- [ ] Sound System Integration

### Phase 6: Quality Assurance
- [ ] Animation Timing Validation
- [ ] Material Quality Check
- [ ] Performance Profiling
- [ ] Cross-Platform Testing
- [ ] Memory Usage Optimization

### Phase 7: Documentation & Tools
- [ ] Migration Tools erstellen
- [ ] Developer Documentation
- [ ] Asset Pipeline Documentation
- [ ] Performance Guidelines

---

## Advanced Weapon System

### Waffen-Erstellung Workflow

#### 1. Modell-Erstellung
```bash
# 3DS Max / SoftImage Workflow
1. Modell, Skin und Animation erstellen
2. Separate .xsi Dateien für jede Animation
3. Carcass .car Datei erstellen
```

#### 2. Carcass Build Process
```bash
# Beispiel .car Datei für M4
$aseanimgrabinit
$aseanimgrab models/weapons/m4/m4menuspin.xsi
$aseanimgrab models/weapons/m4/m4altfire.xsi
$aseanimgrab models/weapons/m4/m4reload.xsi
$aseanimgrab models/weapons/m4/m4fire.xsi
$aseanimgrab models/weapons/m4/m4idle.xsi
$aseanimgrab models/weapons/m4/m4ready.xsi
$aseanimgrab models/weapons/m4/m4dryfire.xsi
$aseanimgrab models/weapons/m4/m4standtoprone.xsi
$aseanimgrab models/weapons/m4/m4pronetostand.xsi
$aseanimgrab models/weapons/m4/m4proneready.xsi
$aseanimgrab models/weapons/m4/m4proneidle.xsi
$aseanimgrab models/weapons/m4/m4pronefire.xsi
$aseanimgrab models/weapons/m4/m4pronedone.xsi
$aseanimgrab models/weapons/m4/m4pronereload.xsi
$aseanimgrabfinalize
$aseanimconvertmdx_noask models/weapons/m4/m4base -makeskel skeletons/weapons/m4/m4
```

#### 3. Build Script
```batch
@echo off
c:
cd c:\Program Files\Soldier of Fortune II - Double Helix\base\models\weapons\m4
c:\Program Files\Soldier of Fortune II - Double Helix\base\carcass -forcebuild m4 > carcassResults.txt
```

#### 4. Output Files
- **m4.glm** - Ghoul2 Model
- **m4.gla** - Animation File
- **m4.frames** - Notetrack File

### Frames File System

#### Notetrack Integration
```python
# Unity Frames Parser
class WeaponFramesParser:
    def __init__(self, frames_file):
        self.frames = {}
        self.parse_frames(frames_file)
    
    def parse_frames(self, file_path):
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('FRAME'):
                    frame_data = self.parse_frame_line(line)
                    self.frames[frame_data['frame']] = frame_data
    
    def get_fire_events(self, animation_name):
        fire_events = []
        for frame, data in self.frames.items():
            if 'fire' in data.get('events', []):
                fire_events.append({
                    'frame': frame,
                    'time': frame / 30.0,  # 30 FPS
                    'event': 'fire'
                })
        return fire_events
```

### Unity Weapon System Implementation

#### Weapon Component Architecture
```csharp
[System.Serializable]
public class WeaponDefinition
{
    [Header("Basic Properties")]
    public string weaponName;
    public WeaponType weaponType;
    public int damage;
    public float fireRate;
    public int maxAmmo;
    public float reloadTime;
    
    [Header("Animation")]
    public AnimationClip fireAnimation;
    public AnimationClip reloadAnimation;
    public AnimationClip idleAnimation;
    public AnimationClip readyAnimation;
    
    [Header("Audio")]
    public AudioClip fireSound;
    public AudioClip reloadSound;
    public AudioClip dryFireSound;
    
    [Header("Effects")]
    public GameObject muzzleFlash;
    public GameObject bulletTrail;
    public GameObject impactEffect;
}

public class WeaponController : MonoBehaviour
{
    [SerializeField] private WeaponDefinition weaponDef;
    [SerializeField] private Animator weaponAnimator;
    [SerializeField] private AudioSource audioSource;
    [SerializeField] private Transform firePoint;
    
    private int currentAmmo;
    private bool isReloading;
    private float lastFireTime;
    
    public void Fire()
    {
        if (CanFire())
        {
            PlayFireAnimation();
            PlayFireSound();
            SpawnMuzzleFlash();
            CreateBulletTrail();
            currentAmmo--;
            lastFireTime = Time.time;
        }
    }
    
    public void Reload()
    {
        if (!isReloading && currentAmmo < weaponDef.maxAmmo)
        {
            StartCoroutine(ReloadCoroutine());
        }
    }
    
    private IEnumerator ReloadCoroutine()
    {
        isReloading = true;
        weaponAnimator.SetTrigger("Reload");
        audioSource.PlayOneShot(weaponDef.reloadSound);
        
        yield return new WaitForSeconds(weaponDef.reloadTime);
        
        currentAmmo = weaponDef.maxAmmo;
        isReloading = false;
    }
}
```

#### Animation Event System
```csharp
public class WeaponAnimationEvents : MonoBehaviour
{
    [SerializeField] private WeaponController weaponController;
    
    // Called from Animation Events
    public void OnFireEvent()
    {
        weaponController.ProcessFireEvent();
    }
    
    public void OnReloadComplete()
    {
        weaponController.OnReloadComplete();
    }
    
    public void OnShellEject()
    {
        // Spawn shell casing
        SpawnShellCasing();
    }
}
```

### Weapon Data Migration

#### JSON Weapon Configuration
```json
{
  "weapons": {
    "m4": {
      "name": "M4A1 Carbine",
      "type": "assault_rifle",
      "damage": 25,
      "fireRate": 0.1,
      "maxAmmo": 30,
      "reloadTime": 2.5,
      "animations": {
        "fire": "m4_fire",
        "reload": "m4_reload",
        "idle": "m4_idle",
        "ready": "m4_ready",
        "dryFire": "m4_dryfire"
      },
      "sounds": {
        "fire": "weapons/m4/fire.wav",
        "reload": "weapons/m4/reload.wav",
        "dryFire": "weapons/m4/dryfire.wav"
      },
      "effects": {
        "muzzleFlash": "effects/muzzle_flash",
        "bulletTrail": "effects/bullet_trail",
        "impact": "effects/bullet_impact"
      }
    }
  }
}
```

#### Weapon Manager
```csharp
public class WeaponManager : MonoBehaviour
{
    [SerializeField] private WeaponDatabase weaponDatabase;
    [SerializeField] private Transform weaponParent;
    
    private Dictionary<string, GameObject> weaponPrefabs = new Dictionary<string, GameObject>();
    private WeaponController currentWeapon;
    
    public void EquipWeapon(string weaponName)
    {
        if (weaponPrefabs.ContainsKey(weaponName))
        {
            // Unequip current weapon
            if (currentWeapon != null)
            {
                Destroy(currentWeapon.gameObject);
            }
            
            // Equip new weapon
            GameObject weaponPrefab = weaponPrefabs[weaponName];
            GameObject weaponInstance = Instantiate(weaponPrefab, weaponParent);
            currentWeapon = weaponInstance.GetComponent<WeaponController>();
        }
    }
    
    public void FireCurrentWeapon()
    {
        if (currentWeapon != null)
        {
            currentWeapon.Fire();
        }
    }
}
```

### Multiplayer Considerations

#### Network Weapon System
```csharp
public class NetworkWeaponController : NetworkBehaviour
{
    [SyncVar] private int currentAmmo;
    [SyncVar] private bool isReloading;
    
    [Command]
    public void CmdFire(Vector3 firePoint, Vector3 direction)
    {
        if (CanFire())
        {
            // Server-side fire logic
            RpcPlayFireEffects(firePoint, direction);
            currentAmmo--;
        }
    }
    
    [ClientRpc]
    private void RpcPlayFireEffects(Vector3 firePoint, Vector3 direction)
    {
        // Play effects on all clients
        SpawnMuzzleFlash(firePoint);
        CreateBulletTrail(firePoint, direction);
    }
}
```

---

## Vertigons (Surface Sprites) System

### Overview
Vertigons sind ein Shader-Pass System für Quake 3 Engine Spiele, das in SoF2 und JK2 verwendet wird. Sie ermöglichen das Platzieren von 3D-Objekten auf Oberflächen, die senkrecht von der Oberfläche abstehen.

### Surface Sprites Syntax
```bash
surfaceSprites <type> <width> <height> <density> <fadedist>
```

#### Types:
- **vertical**: Objekte die senkrecht abstehen (Gras, Schilf)
- **oriented**: Immer zur Kamera zeigende Objekte (Felsen, Trümmer)
- **effect**: Animierte Objekte mit Wachstum/Fade-Effekten

#### Beispiel Shader:
```bash
textures/test/grnd01c_sprites
{
    q3map_nolightmap
    q3map_onlyvertexlighting
    {
        map textures/kamchatka/grnd01c
        blendFunc GL_DST_COLOR GL_ZERO
    }
    {
        map models/objects/colombia/jungle/tall_grass
        surfaceSprites vertical 16 32 48 1000 
        ssVariance 1.0 2.0 
        ssWind 1.0
        blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
        alphaFunc GE128
        depthWrite
    }
}
```

### Unity Implementation
```csharp
public class SurfaceSpriteRenderer : MonoBehaviour
{
    [SerializeField] private GameObject spritePrefab;
    [SerializeField] private float density = 48f;
    [SerializeField] private float fadeDistance = 1000f;
    [SerializeField] private Vector2 size = new Vector2(16, 32);
    
    public void GenerateSprites(MeshRenderer surface)
    {
        Vector3[] vertices = surface.GetComponent<MeshFilter>().mesh.vertices;
        
        for (int i = 0; i < vertices.Length; i += Mathf.RoundToInt(density))
        {
            if (vertices[i].y > 0.1f) // Nur auf horizontalen Flächen
            {
                Vector3 worldPos = surface.transform.TransformPoint(vertices[i]);
                GameObject sprite = Instantiate(spritePrefab, worldPos, Quaternion.identity);
                sprite.transform.parent = transform;
                
                // Zufällige Größe und Rotation
                float randomScale = Random.Range(0.5f, 1.5f);
                sprite.transform.localScale = new Vector3(size.x * randomScale, size.y * randomScale, 1);
                sprite.transform.rotation = Quaternion.Euler(0, Random.Range(0, 360), 0);
            }
        }
    }
}
```

---

## Advanced Weapon System Details

### Weapon Hierarchy Structure
```bash
model_root
    mesh_root
        bodyfront (LOD0)
            barrel, clip, frontsight, gunbody, etc.
        bodyfront_1 (LOD1)
            barrel_1, clip_1, frontsight_1, etc.
        bodyfront_2 (LOD2)
            barrel_2, clip_2, frontsight_2, etc.
    skeleton_root
        gun (main bone)
            bolt1, bolt2, clip1, clip2, door
            option1-8, stock, trigger
```

### Frames File System
```bash
# Beispiel M4.frames
s:/ani/base/models/weapons/m4/m4fire.xsi
{
    "startframe"    "451"
    "duration"      "2"
    "fps"           "20"
    "averagevec"    "0.000 0.000 0.000"
    
    notetrack
    {
        "frame"     "1"
        "note"      "fire"
    }
}
```

### WPN File Structure
```bash
weapon
{
    name            "M4"
    displayName     "WEAPONS_NAME_M4"
    model           "models/weapons/m4/world/m4world.glm"
    safe            true
    rank            0.5
    cvar            wp_m4
    category        5
    
    attack
    {
        ammoType        "5.56mm"
        clipSize        "30"
        damage          "70"
        muzzleFlash     "effects/muzzle_flashes/mflash_m4"
        inaccuracy      ".05"
        maxInaccuracy   ".8"
        range           8192
        kickAngles      "1 4 -2 1"
        
        fireModes
        {
            mode1       single
            mode2       burst
            mode3       auto
        }
    }
}
```

---

## Character Skins System

### Base Models
- **Average_Armor**: Männlich, gepanzert, Militäruniform
- **Average_Sleeves**: Männlich, Militäruniform
- **Chem_Suit**: Chemikalienschutzanzug
- **Fat**: Männlich, schwerer Körperbau
- **Female_Armor**: Weiblich, gepanzert
- **Female_Pants**: Weiblich, kurze Ärmel, lange Hose
- **Female_Skirt**: Weiblich, kurze Ärmel, Rock
- **Snow**: Männlich, dicker Mantel
- **Suit_Long_Coat**: Männlich, langer Mantel
- **Suit_Sleeves**: Männlich, kurze Ärmel

### Hairstyles
**Männlich**: Bald, Medium (avmed), Medium mit Hut (avmedhat), Lang (avlong), Bart, Schnurrbart (avmst)
**Weiblich**: Bald, Kurz (fshort), Lang (flong), Dutt (_bun), Pferdeschwanz (_pony)

### Shader Setup
```bash
models/characters/female_face/f_taylor
{
    q3map_nolightmap
    q3map_onlyvertexlighting
    hitLocation    models/characters/female_face/f_female_hit
    {
        map models/characters/female_face/f_taylor
        rgbGen lightingDiffuse
    }
}
```

---

## Terrain System

### GenSurf Terrain
- Verwendet Heightmaps für Terrain-Generierung
- Metashader-System für Textur-Blending
- Alphamap-basierte Textur-Verteilung

### ARIOCHE Terrain
- Algorithmus-basierte Terrain-Generierung
- Runtime-Generierung für größere Terrains
- Verwendet im Random Mission Generator

### Metashader Example
```bash
textures/metashader/col3_0
{
    q3map_nolightmap
    q3map_onlyvertexlighting
    q3map_vertexshadows
    {
        map textures/colombia/mudside_b
        rgbGen vertex
        tcMod scale .25 .25
    }
}

textures/metashader/col3_0to1
{
    q3map_nolightmap
    q3map_onlyvertexlighting
    q3map_vertexshadows
    {
        map textures/colombia/mudside_b
        rgbGen vertex
        alphaGen vertex
        tcMod scale .25 .25
    }
    {
        map textures/colombia/grass_side
        blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
        rgbGen vertex
        alphaGen vertex
        tcMod scale .25 .25
    }
}
```

---

## Multiplayer Map System

### Spawn Entities
- **info_player_deathmatch**: Standard Deathmatch Spawns
- **gametype_player**: Spezielle SoF2 Entity für Elimination/Infiltration

### Mission Items
- **gametype_item**: Mission-spezifische Objekte
- Benötigt targetname und gametype Werte
- Beispiele: briefcase, flag, etc.

### Gametype Triggers
- **gametype_trigger**: Aktivierung von Mission-Items
- Platzierung abhängig vom Gametype
- CTF: Um die Flagge, Infiltration: Am Zielort

### Unity Multiplayer Implementation
```csharp
public class MultiplayerMapManager : NetworkBehaviour
{
    [SerializeField] private Transform[] spawnPoints;
    [SerializeField] private GameObject[] missionItems;
    
    [ServerRpc]
    public void SpawnPlayer(NetworkConnection conn)
    {
        Transform spawnPoint = GetRandomSpawnPoint();
        GameObject player = Instantiate(playerPrefab, spawnPoint.position, spawnPoint.rotation);
        NetworkServer.Spawn(player, conn);
    }
    
    [ServerRpc]
    public void ActivateMissionItem(string itemName)
    {
        GameObject item = missionItems.FirstOrDefault(x => x.name == itemName);
        if (item != null)
        {
            item.SetActive(true);
            RpcShowMissionItem(itemName);
        }
    }
    
    [ClientRpc]
    private void RpcShowMissionItem(string itemName)
    {
        // Show mission item to all clients
        UIManager.Instance.ShowMissionObjective(itemName);
    }
}
```

---

## Fazit

Diese erweiterte Zusammenfassung bietet eine vollständige Übersicht über das SoF2 Modding-System und eine detaillierte Anleitung für die Portierung nach Unity. Das modulare Design des ursprünglichen Systems lässt sich gut in Unity's Component-System übertragen, wobei die JSON-basierten Konfigurationen eine flexible und erweiterbare Basis bieten.

### Wichtigste Erweiterungen:
- **Vollständiges Waffen-System** mit Carcass Build Process
- **ROFF Animation System** für Weltobjekte
- **Advanced Material System** mit Custom Shadern
- **Performance Optimization** mit LOD System
- **Dynamic Equipment System** für flexible Ausrüstung
- **AI Behavior System** für intelligente NPCs
- **Animation Event System** für präzise Timing-Kontrolle
- **Network-ready Architecture** für Multiplayer-Support

### Die wichtigsten Vorteile der Unity-Portierung:
- **Moderne Rendering-Pipeline** mit besseren Shadern
- **Flexible Animation-System** mit Animator Controller
- **Component-basierte Architektur** für bessere Modularität
- **Cross-Platform Support** für verschiedene Zielplattformen
- **Bessere Performance** durch optimierte Rendering-Pipeline
- **Erweiterte AI-Systeme** mit Behavior Trees
- **Skalierbare LOD-Systeme** für große Welten
- **Einfache Asset-Pipeline** für schnelle Iteration
- **Modularer Component-Ansatz** für einfache Erweiterbarkeit


## Models und ParentTemplate NPC Files

### **Model-Formate in SoF2:**

**1. MD3 Models:**
- Für statische Modelle
- Dateiendung: `.md3`
- Einfacher zu erstellen als Ghoul2

**2. Ghoul2 Models (GLM):**
- Für ConfusEd Entities (Singleplayer), Bolt-ons und Charaktere
- Dateiendung: `.glm`
- Zwei Varianten:
  - **Mit Bones:** Für animierte Modelle (Charaktere, einige ConfusEd Modelle)
  - **Ohne Bones:** Für nicht-animierte Modelle (Bolt-ons)

### **ParentTemplate System:**

**Vererbung:**
- Jedes NPC Template hat ein **ParentTemplate**
- Kind-Templates erben Werte vom Parent, wenn sie nicht selbst definiert sind
- Beispiel: "Colombian Rebel" als Basis für spezialisierte Varianten

**GroupInfo Konfiguration:**
```cpp
GroupInfo
{
    Skeleton        "average_sleeves.skl"
    ParentTemplate  "NPC_Prometheus_Soldier"
}
```

### **NPC File Konfigurationen:**

**1. Grundlegende Felder:**
- **Name:** Template-Name
- **Team:** Zugehörigkeit (z.B. "The Shop")
- **Rank:** Civilian, Criminal, Private, Sergeant
- **Occupation:** Assassin, Commando, Demolitionist, etc.
- **Accuracy:** Treffgenauigkeit (0.0-1.0)

**2. Skins:**
- Jeder Charakter kann mehrere Skins haben
- Zufällige Auswahl beim Spawnen
- Vererbung von Parent-Templates
- Skin-spezifische Inventar-Konfigurationen möglich

**3. Inventar-System:**
- **Global Inventory:** Wird an alle Charaktere vererbt
- **Skin Inventory:** Nur bei spezifischem Skin aktiv
- **Bolt-Punkte:** Für Waffen und Items am Charakter
- **Chance-Feld:** Wahrscheinlichkeit für Item-Spawn (1-100%)

**4. Waffen-Konfiguration (nur Singleplayer):**
- Alle Waffen in `SOF2.item` und `SoF2.wpn` definiert
- Spezielle NPC-Felder erforderlich:
  - `canholster`: Kann eingesteckt werden
  - `holstmodel`: Holster-Modell
  - `canshootoff`: Kann aus der Hand geschossen werden
  - `clips`: Munitionsmenge

**5. Items:**
- Bolt-ons für Aussehen
- Oberflächen zum Ein-/Ausschalten
- Verwendbare Items (Zigaretten, Rauchgranaten)
- Schutz- und Schadensfunktionen

**6. Multiplayer-spezifische Felder:**
- **FormalName:** Name im Multiplayer-Menü
- **Deathmatch:** Bestimmt Multiplayer-Gültigkeit

### **Wichtige technische Details:**
- Templates verwenden geschweifte Klammern-Syntax
- Vererbung funktioniert kumulativ (keine Redundanz-Prüfung)
- Parent Templates meist in `base.NPC`
- Fast alle männlichen Charaktere von "Base Human" abgeleitet

Das System ermöglicht es, durch Vererbung effizient neue Charaktertypen zu erstellen und Änderungen zentral zu verwalten.


Zusammenfassung: SoF2_Character_NPCFile.doc
Diese Dokumentation beschreibt das NPC (Non-Player Character) Template-System für das Spiel Soldier of Fortune 2 (SoF2) von Raven Software.
Hauptthemen:
1. Überblick (1.0)
Alle Charaktere in SoF2Radiant werden in externen Textdateien definiert
Diese Templates enthalten Skins, Statistiken und Inventar-Konfigurationen
Neue Charaktertypen können einfach durch Hinzufügen von Templates erstellt werden
Dateien haben die Erweiterung .NPC und befinden sich im base/npcs/ Verzeichnis
2. Vererbung (2.0)
Wichtiges Feature: Jedes Template hat ein "Parent Template"
Kind-Templates erben Werte vom Parent, wenn sie nicht selbst definiert sind
Beispiel: "Colombian Rebel" als Basis für spezialisierte Varianten
Erleichtert das Erstellen neuer Templates und das Ändern bestehender
3. Berufe und Ränge (3.0) - Nur Singleplayer
Ränge: Civilian, Criminal, Private, Sergeant
Berufe: Assassin, Commando, Demolitionist, Emplaced Gunner, Look Out, Scout, Script Guy, Sniper, Soldier, Soldier Elite, Soldier Cover, Tourist, Thug
Jeder Beruf hat spezifische Verhaltensweisen und Fähigkeiten

4. Inventar-System (4.0)
Global Inventory: Wird an alle Charaktere und Skins vererbt
Skin Inventory: Nur bei Auswahl des entsprechenden Skins aktiv
Waffen und Items können mit "Bolt"-Punkten am Charakter befestigt werden
"Chance"-Feld bestimmt Wahrscheinlichkeit für Item-Spawn (1-100%)
5. Multiplayer-spezifische Felder (4.5)
FormalName: Name im Multiplayer-Menü
Deathmatch: Bestimmt, ob NPC für Multiplayer gültig ist
6. Waffen (5.0) - Nur Singleplayer
Alle Waffen sind in der SOF2.item Datei definiert
Zusätzlich benötigen sie Einträge in der SoF2.wpn Datei
Spezielle Felder für NPC-Nutzung erforderlich
Wichtige technische Details:
Templates verwenden eine spezielle Syntax mit geschweiften Klammern
GroupInfo definiert Skeleton und Parent Template für ganze Dateien
Vererbung funktioniert kumulativ (keine Redundanz-Prüfung)
Datei enthält auch umfangreiche Tabellen und Referenzmaterialien
Die Dokumentation ist sehr detailliert und dient als vollständige Anleitung für Modder, die neue Charaktere für SoF2 erstellen möchten.

Ich schaue mir deine ZUSAMMENFASSUNG.md und die relevanten Dokumentationen an, um herauszufinden, was du für den Export von .frames und Animationen in Blender benötigst.


Basierend auf der Dokumentation und deiner ZUSAMMENFASSUNG.md kann ich dir jetzt eine umfassende Antwort geben, was du für den Export von .frames und Animationen in Blender benötigst:

## **Export von .frames und Animationen für SoF2 Models in Blender**

### **Was du benötigst:**

**1. Workflow für animierte GLM Models (mit Bones):**

**Schritt 1: Model-Vorbereitung**
- Erstelle dein Model in Blender
- Füge Bones hinzu und rigge das Model
- Verwende Skin-Modifier für Vertex-Weighting
- **Wichtig:** Jeder Vertex muss gewichtet werden (100% Gewichtung)

**Schritt 2: Animation erstellen**
- Animiere dein Model (max. ~25 Frames empfohlen)
- Stelle sicher, dass die Animation korrekt funktioniert

**Schritt 3: Export zu XSI**
- Exportiere als **XSI-Format** (nicht direkt GLM)
- Benötigst **XSIImporter Plugin** für Blender/3DS Max
- Export-Pfad: `base/models/objects/[kategorie]/[modelname]/`

**Schritt 4: CAR-Datei erstellen**
Erstelle eine `.CAR` Datei im gleichen Verzeichnis:
```bash
$aseanimgrabinit
$aseanimgrab models/objects/[kategorie]/[modelname]/[modelname].xsi
$aseanimgrabfinalize
$aseanimconvertmdx_noask models/objects/[kategorie]/[modelname]/[modelname] -makeskel c:/[gamepath]/base/skeletons/objects/[kategorie]/[modelname]/[modelname]
```

**Schritt 5: Carcass-Kompilierung**
```bash
C:\Program Files\Soldier of Fortune II\bin\carcass c:\Program Files\Soldier of Fortune II\base\models\objects\[kategorie]\[modelname]\[modelname] > carcassResults.txt
```

**Ergebnis:**
- `.glm` Datei im Model-Verzeichnis
- `.gla` Datei im `base/skeletons/` Verzeichnis  
- **`.frames` Datei** im `base/skeletons/` Verzeichnis

### **Wichtige technische Details:**

**Für Blender-spezifische Anpassungen:**
- **Skalierung:** SoF2 verwendet spezielle Skalierung (15.24x Faktor)
- **FPS:** 20 Frames pro Sekunde für korrekte Geschwindigkeit
- **Grid:** 8.0 Einheiten Grid-Spacing
- **Texturen:** PNG/JPG Format verwenden

**Animation-Limits:**
- Maximal ~25 Frames pro Animation
- Alle Vertices müssen gewichtet sein
- Keine doppelten Skin-Modifier verwenden

### **Was du in Blender implementieren musst:**

**1. XSI Export-Plugin:**
- Du benötigst einen XSI-Exporter für Blender
- Dieser muss die SoF2-spezifischen XSI-Formate unterstützen

**2. Animation-Export-Funktionalität:**
- Export der Bone-Animationen
- Korrekte Frame-Zuordnung
- Skeleton-Informationen

**3. Automatisierung:**
- CAR-Datei-Generierung
- Carcass-Tool-Integration
- Fehlerbehandlung

### **Alternative für Blender:**

Da die ursprüngliche Dokumentation für 3DS Max geschrieben wurde, musst du für Blender:

1. **XSI-Export-Plugin** entwickeln oder finden
2. **Carcass-Tool-Integration** implementieren
3. **Animation-Pipeline** anpassen

**Oder:** Du könntest den Workflow über 3DS Max laufen lassen und nur die Modelle in Blender erstellen, dann nach 3DS Max exportieren für den finalen SoF2-Export.

Die `.frames` Dateien enthalten die Animation-Daten und werden automatisch vom Carcass-Tool generiert, wenn du die korrekte XSI-Datei mit Animationen exportierst.
