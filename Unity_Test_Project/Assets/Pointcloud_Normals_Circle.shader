Shader "Vertex Colored Alpha Surf Shader" {
	Properties {
	}
	SubShader {
		Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" }
		LOD 200
		
		CGPROGRAM
		#pragma surface surf Lambert alpha
		
		sampler2D _MainTex;

		struct Input {
			float4 color: Color; // Vertex color
		};

		void surf (Input IN, inout SurfaceOutput o) {
			o.Albedo = IN.color.rgb; // vertex RGB
			o.Alpha = 1; // vertex Alpha
		}
		ENDCG
	} 
	FallBack "Diffuse"
}
