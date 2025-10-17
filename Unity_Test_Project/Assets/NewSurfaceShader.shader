Shader "Custom/NormalTest"
{
    Properties
    {
       _MainTex ("UV (DontUse)", 2D) = "white" {} 
       [ToggleOff] _SpecularHighlights("Specular Highlights", Float) = 1.0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        LOD 200

        CGPROGRAM
        // Physically based Standard lighting model, and enable shadows on all light types
        #pragma surface surf Lambert
        
        sampler2D _MainTex;

        struct Input
        {
            float4 color: Color;
            float2 uv_MainTex;
        };

        void surf (Input IN, inout SurfaceOutput o)
        {
            o.Albedo.rgb = IN.color.rgb;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
