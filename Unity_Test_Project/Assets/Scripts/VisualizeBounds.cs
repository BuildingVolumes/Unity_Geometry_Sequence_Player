using Sirenix.OdinInspector;
using UnityEngine;

public class VisualizeBounds : MonoBehaviour
{
  private void OnDrawGizmos()
  {
    Bounds bounds = GetComponent<MeshRenderer>().bounds;
    Gizmos.DrawWireCube(bounds.center, bounds.size);
  }
}
