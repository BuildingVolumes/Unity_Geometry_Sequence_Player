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

To enhance the appearance of your sequences, you can apply your own custom Materials and Shaders.

## Mesh sequences

![Difference between the default material and a custom material](Mesh_Material_Difference.jpg)

### Assigning materials

![The material options](Mesh_Material_Options.png)

Assigning a material to a mesh sequence works nearly identical as it is for every other mesh in Unity. But instead of assigning your material in the mesh renderer, you have to go to the **Geometry Sequence Stream** component that can be found on the same Gameobject as your _Geometry Sequence Player_. Under **Mesh settings** you can find the **Mesh Material** slot, where you can assign your material.

> ☝️ Please note that  the sequence thumbnail in the editor might not always be updated automatically. Sometimes you need to enter the playmode once so that changes are visible.

### Texture slot assignment

If you have a mesh sequence with textures, you can also control to which texture slot the texture will be applied. By default, textures will always be applied to the Main/Albedo/Diffuse slot, which is defined in the shader as _\_MainTexture_. But you can also apply the texture to any other slot. Either you select one or more predefined slots in the **Apply to texture slots** variable, or you enter the name of the texture slot into the **Custom texture slots** list. This has to be the name of the texture slot as found in the **shader**, not the material! Shader texture slot variables are often prefixed with an _Underscore.

## Pointcloud sequences

Changing the appearance of the pointcloud works very different compared to meshes, as pointclouds require special shaders for rendering correctly. However, there are some predefined settings you can use to easily and quickly change pointcloud appearance settings. These settings can be found under the **Geometry Sequence Stream** component. If you are already familiar with writing Shaders for Unity, you can also directly edit the pointcloud shaders.

![Pointcloud Settings](Pointcloud_Settings.png)

### Pointcloud size

![Pointcloud size difference](Pointcloud_Size.jpg)

With the pointcloud size parameter, you control the size of each point in Unity units. Usually 0.01 - 0.02 is a good range for most sequences.

### Pointcloud shape

![Pointcloud shape difference](Pointcloud_Shape.jpg)

The pointcloud shape lets you switch between different point rendering options. There are **Quads**, **Circles** and **Splats (Experimental)**. **Quads** are the default setting and look like pixels. For a softer look, **Circles** are a good choice, but you might need to adjust the size a bit. **Splats** are half-transparent circles, which give the softest look, but they are not yet fully implemented and will look strange most of the time.

### Pointcloud emission

![Pointcloud emission difference](Pointcloud_Emission.jpg)

The pointcloud material is emissive by default, to give a look similar to an unlit material. You can disable the emission by setting this value to 0, or turn it up higher, to give points a glowing ember like look. You need to enable bloom in your URP/HDRP volume settings to fully benefit from the emissive effect.

### (Advanced) Editing the pointcloud shader

You can also directly edit the Pointcloud shaders to more finely tune the appearance of the points. You will need some experience with writing shaders for Unitys Shaderlab/GLSL and/or Shadergraph. You can find the shaders under:

`Packages > Geometry Sequence Player > Runtime > Shader > Resources`

You'll see two different sets of shaders, three shaders written in Shaderlab, and three ShaderGraphs, with a _RT suffix. For the moment, the Shadergraph shaders are only used when the Polyspatial/Bounded rendering path of the Apple Vision Pro is used, otherwise the Shaderlab Shaders will be used.
