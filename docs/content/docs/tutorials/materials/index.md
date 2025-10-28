---
title: "Materials and Shaders"
description: "Modifying the sequence's appearance"
lead: "Modifying the sequence's appearance"
date: 2020-11-16T13:59:39+01:00
lastmod: 2020-11-16T13:59:39+01:00
draft: false
images: []
menu:
  docs:
    parent: "tutorials"
weight: 165
toc: true
---

## Intro

To enhance the appearance of your sequences, you can apply your own custom Materials and Shaders. If you don't supply a material, an appropriate default material will be automatically assigned.

By default, an **unlit** material will be assigned to the sequence, which means they won't be affected by the scene lighting. Lit materials can either be created by yourself, or you can use one of the materials available under `Packages/Geometry Sequence Player/Runtime/Materials/Your selected Renderpath`

## Mesh sequences

Assigning a custom  material to a mesh sequence works nearly the same as for any other mesh in Unity. All shaders and Shadergraph Materials can be used.

![Difference between the default material and a custom material](Mesh_Material_Difference.jpg)

### Assigning materials

![The material options](Mesh_Material_Options.png)

Go to the **Geometry Sequence Stream** component that can be found on the same Gameobject as your _Geometry Sequence Player_. At the top you can find the **Custom Material** slot, where you can assign your material. If you assign a material there, the **Instantiate Material** checkbox will also show up. This let's you choose if your material should either be copied (instantiated) before applying it, or the material should just be assigned. In the latter case, any changes made to the material file itself will be instantly reflected on the sequence.

> ☝️ Please note that  the sequence thumbnail in the editor might not always be updated automatically. Sometimes you need to enter the playmode once so that changes are visible.

### Texture slot assignment

If you have a mesh sequence with textures, you can also control to which texture slot the texture will be applied. By default, textures will always be applied to the Main/Albedo/Diffuse slot, which is defined in the shader as _\_MainTexture_. But you can also apply the texture to any other slot. Either you select one or more predefined slots in the **Apply to texture slots** variable, or you enter the name of the texture slot into the **Custom texture slots** list. This has to be the name of the texture slot as found in the **shader**, not the material! Shader texture slot variables are often prefixed with an _Underscore.

## Pointcloud sequences

Changing the appearance of the pointcloud works very differently compared to meshes, as pointclouds require special shaders for rendering correctly. If you don't assign a custom pointcloud material, there are some predefined settings you can use to easily and quickly the appearance. These settings can be found under the **Geometry Sequence Stream** component and include the **Point Size** as well as the **Point Emission Strength**.

![Pointcloud Settings](Pointcloud_Settings.png)

### Pointcloud Render Path

The Geometry Sequence Player supports three different render paths:

- **ShaderGraph**
- **Legacy**
- **Polyspatial**

In Unity, there are two basic ways to create shaders. You can either code them yourselves, or use the visual coding tool _Shadergraph_. Both paths are supported by the Geometry Sequence Player, and with this option you can manually choose which should be used. For HDRP, URP and built-in (with the shadergraph package installed), we recommend the **Shadergraph** path. If you are more comfortable with coding shaders, or you use the built-in render without the shadergraph package, the **Legacy** render path is right for you. The **Polyspatial** render path should only be used when working with the Apple Vision Pro.

### Pointcloud size

![Pointcloud size difference](Pointcloud_Size.jpg)

With the pointcloud size parameter, you control the size of each point in Unity units. Usually 0.01 - 0.02 is a good range for most sequences.

### Pointcloud emission

![Pointcloud emission difference](Pointcloud_Emission.jpg)

The pointcloud material is emissive by default, to give a look similar to an unlit material. You can disable the emission by setting this value to 0, or turn it up higher, to give points a glowing ember like look. You need to enable bloom in your URP/HDRP volume settings to fully benefit from the emissive effect.

### Customising the pointcloud shader

![Pointcloud shadergraph example](shadergraph-distortion.jpg)

If you don't set a custom material, a default pointcloud material will be loaded that is appropriate for the chosen rendering path. You can create your own Pointcloud shaders to more finely tune the appearance of the points. You will need some experience with writing shaders for Unitys Shaderlab/GLSL and/or Shadergraph. We strongly recommend to take a look at the [Shadergraph Example](/Unity_Geometry_Sequence_Player/docs/tutorials/materials/samples/#sample-05-shadergraph) and clone one of the available pointcloud shaders found under:

`Packages > Geometry Sequence Player > Runtime > Shader > Resources`

You'll see three different sets of shaders, _Legacy_, _Shadergraph_ and _Polyspatial_. Clone one of the shaders appropriate for your chosen render path. Then, create a material that uses your freshly cloned shader and apply it under **Custom Material**. For quick iteration, we recommend to disable the **Instantiate Shader** option. If you're a little bit familiar with Shaderlab/Shadergraph, you should be able to get an idea of how the shaders work, by taking a look at the commented code/graph.
