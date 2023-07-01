using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;


public class CollisionAssetPostprocessor : AssetPostprocessor
{
    private struct AxisScaleInfo
    {
        public float scale;
        public int axis;

        public AxisScaleInfo(float value, int axis)
        {
            this.scale = value;
            this.axis = axis;
        }

        public static int Compare(AxisScaleInfo a, AxisScaleInfo b)
        {
            return a.scale.CompareTo(b.scale);
        }
    }

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

    // remove .### ending from socket objects
    private void RenameSocketObject(GameObject gameObject)
    {
        string objName = gameObject.name;
        if (objName.StartsWith("SOCKET_"))
        {
            bool shouldRename = false;
            int nameLen = objName.Length;
            if (nameLen > 4)
            {
                if (objName[nameLen - 4] == '.')
                {
                    for (int i = nameLen - 3; i < nameLen; ++i)
                    {
                        if (char.IsDigit(objName[i]))
                        {
                            shouldRename = true;
                        }
                    }
                }
            }
            if (shouldRename)
            {
                gameObject.name = objName.Substring(0, nameLen - 4);
            }
        }
    }

    private void AddCollider(Transform t, List<Transform> transformsToDestroy)
    {
        foreach (Transform child in t.transform)
        {
            AddCollider(child, transformsToDestroy);
        }

        RenameSocketObject(t.gameObject);

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
            GetCapsuleDimensions(t, out float height, out float radius, out int axis);
            capsuleCollider.height = height;
            capsuleCollider.radius = radius;
            capsuleCollider.direction = axis;
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

    void GetCapsuleDimensions(Transform t, out float height, out float radius, out int axis)
    {
        Vector3 scale = t.localScale;
        AxisScaleInfo[] axisScaleInfos = {
            new AxisScaleInfo(scale.x, 0),
            new AxisScaleInfo(scale.y, 1),
            new AxisScaleInfo(scale.z, 2)
        };
        
        Array.Sort(axisScaleInfos, AxisScaleInfo.Compare);

        AxisScaleInfo longestAxis = axisScaleInfos[2];
        AxisScaleInfo secondLongestAxis = axisScaleInfos[1];

        height = longestAxis.scale;
        radius = secondLongestAxis.scale * .5f;
        axis = longestAxis.axis;
    }
}