using System.Collections.Generic;
using UnityEditor;
using UnityEngine;


public class CollisionAssetPostprocessor : AssetPostprocessor
{
    public void OnPostprocessModel(GameObject gameObject)
    {
        Debug.Log("CollisionAssetPostprocessor started");

        List<Transform> transformsToDestroy = new List<Transform>();
        
        foreach (Transform child in gameObject.transform)
        {
            AddCollider(child, transformsToDestroy);
        }

        foreach (Transform t in transformsToDestroy)
        {
            GameObject.DestroyImmediate(t.gameObject);
        }

        Debug.Log("CollisionAssetPostprocessor finished");
    }

    private void AddCollider(Transform t, List<Transform> transformsToDestroy)
    {
        foreach (Transform child in t.transform)
        {
            AddCollider(child, transformsToDestroy);
        }

        string meshName;
        if (t.gameObject.TryGetComponent(out MeshFilter meshFilter))
        {
            meshName = meshFilter.sharedMesh.name;
        }
        else return;

        if (meshName.StartsWith("UBX_"))
        {
            BoxCollider boxCollider = t.parent.gameObject.AddComponent<BoxCollider>();
            boxCollider.center = t.localPosition;
            boxCollider.size = t.localScale;
            transformsToDestroy.Add(t);
        }
        else if (meshName.StartsWith("USP_"))
        {
            SphereCollider sphereCollider = t.parent.gameObject.AddComponent<SphereCollider>();
            sphereCollider.center = t.localPosition;
            sphereCollider.radius = t.localScale.z * .5f;
            transformsToDestroy.Add(t);
        }
        else if (meshName.StartsWith("UCP_"))
        {
            CapsuleCollider capsuleCollider = t.parent.gameObject.AddComponent<CapsuleCollider>();
            transformsToDestroy.Add(t);
        }
        else if (meshName.StartsWith("UCX_"))
        {
            MeshCollider meshCollider = t.parent.gameObject.AddComponent<MeshCollider>();
            meshCollider.convex = true;
            if (t.gameObject.TryGetComponent<MeshFilter>(out MeshFilter mesh))
            {
                meshCollider.sharedMesh = mesh.sharedMesh;
            }
            transformsToDestroy.Add(t);
        }
    }
}