using System.IO;
using UnityEditor;
using UnityEngine;
using Newtonsoft.Json.Linq;
using System;
using BuildingVolumes.Player;
using UnityEngine.Playables;
using UnityEngine.Timeline;
using System.Collections.Generic;
using UnityEditor.SceneManagement;
using GluonGui.WorkspaceWindow.Views.WorkspaceExplorer.Explorer;

public class BumpUpPackageVersionAndCopySamples : EditorWindow
{
  const string relativePathToPackageSamples = "Samples~\\SequenceSamples";
  const string relativePathToImportedSamples = "Samples\\Geometry Sequence Player";
  const string SequencesSamplesFolderName = "Sequence Samples";

  string currentPackagePath = "";
  string currentPackageJsonPath = "";
  string currentVersion = "";
  string packageJSONContent;
  int newMajor;
  int newMinor;
  int newPatch;

  const string packagePathEditorPrefsKey = "UGGS_Package_Path";

  [MenuItem("UGGS Package/Increment package version and copy samples")]
  static void Init()
  {
    BumpUpPackageVersionAndCopySamples window = GetWindow<BumpUpPackageVersionAndCopySamples>();

    window.titleContent = new GUIContent("Change package versioning");
    window.ShowPopup();
  }

  private void CreateGUI()
  {
    string packagePath = EditorPrefs.GetString(packagePathEditorPrefsKey);
    bool pathValid = false;

    while (!pathValid)
    {
      currentPackageJsonPath = Path.Combine(packagePath, "package.json");

      if (!File.Exists(currentPackageJsonPath))
      {
        EditorUtility.DisplayDialog("Path invalid!", "Path to package not found! Please change the path now", "Ok");

        string newPathToPackage = EditorUtility.OpenFolderPanel("Select Package folder", packagePath, "");
        if (newPathToPackage == String.Empty)
          break;
        else
          packagePath = newPathToPackage;
      }

      else
      {
        pathValid = true;
      }
    }

    if (!File.Exists(currentPackageJsonPath))
    {
      Debug.LogError("Could not find package.json in: " + currentPackageJsonPath);
      GetWindow<BumpUpPackageVersionAndCopySamples>().Close();
      return;
    }

    currentPackagePath = packagePath;
    EditorPrefs.SetString(packagePathEditorPrefsKey, packagePath);
    GetCurrentPackageVersion(currentPackageJsonPath);
  }

  void OnGUI()
  {
    GUILayout.Space(20);
    EditorGUILayout.LabelField("Current package version is: " + currentVersion, EditorStyles.wordWrappedLabel);
    GUILayout.Space(20);
    EditorGUILayout.LabelField("Change version to:", EditorStyles.wordWrappedLabel);
    GUILayout.BeginHorizontal();
    newMajor = EditorGUILayout.IntField(newMajor);
    newMinor = EditorGUILayout.IntField(newMinor);
    newPatch = EditorGUILayout.IntField(newPatch);
    GUILayout.EndHorizontal();

    string newVersion = newMajor + "." + newMinor + "." + newPatch;

    string absPathToUpgradedImportedSamplesFolder = Path.Combine(Application.dataPath, relativePathToImportedSamples, newVersion, SequencesSamplesFolderName);
    string absPathToUpgradedPackageSamplesFolder = Path.Combine(currentPackagePath, relativePathToPackageSamples);

    if (GUILayout.Button("Change Version and copy samples"))
    {
      UpdateSamples(currentVersion, newVersion);
      CopySamples(absPathToUpgradedImportedSamplesFolder, absPathToUpgradedPackageSamplesFolder);
      UpdatePackageJSONAndSave(currentPackageJsonPath, packageJSONContent, newVersion);
      GetCurrentPackageVersion(currentPackageJsonPath);
      EditorUtility.SetDirty(this);
    }

    if (GUILayout.Button("Just copy samples"))
    {
      CopySamples(absPathToUpgradedImportedSamplesFolder, absPathToUpgradedPackageSamplesFolder);
      GetCurrentPackageVersion(currentPackageJsonPath);
      EditorUtility.SetDirty(this);
    }
  }

  void GetCurrentPackageVersion(string pathToPackageJSON)
  {
    packageJSONContent = File.ReadAllText(pathToPackageJSON);

    JObject o = JObject.Parse(packageJSONContent);

    JToken version = o.GetValue("version");
    currentVersion = version.Value<string>();
    string[] versionValues = currentVersion.Split('.');
    int major = Int32.Parse(versionValues[0]);
    int minor = Int32.Parse(versionValues[1]);
    int patch = Int32.Parse(versionValues[2]);

    newMajor = major;
    newMinor = minor;
    newPatch = patch;
  }

  void UpdatePackageJSONAndSave(string pathToJson, string jsonContent, string newVersion)
  {
    JObject obj = JObject.Parse(jsonContent);
    obj["version"] = newVersion;

    try
    {
      File.WriteAllText(pathToJson, obj.ToString());
    }

    catch
    {
      Debug.LogError("Could not update package JSON!");
      return;
    }

    Debug.Log("Changed JSON package version to " + newVersion);

  }

  void UpdateSamples(string currentVersion, string newVersion)
  {
    string relativePathToImportedSequenceSamplesFolder = Path.Combine(relativePathToImportedSamples, currentVersion, SequencesSamplesFolderName);

    string pathToBasicSceneMesh = Path.Combine(relativePathToImportedSequenceSamplesFolder, "01_Basic_Example.unity");
    string pathToBasicScenePC = Path.Combine(relativePathToImportedSequenceSamplesFolder, "02_Pointcloud_Example.unity");
    string pathToTimelineScene = Path.Combine(relativePathToImportedSequenceSamplesFolder,"03_Timeline_Example.unity");
    string pathToAPIScene = Path.Combine(relativePathToImportedSequenceSamplesFolder, "04_API_Example.unity");
    string pathToShadergraphScene = Path.Combine(relativePathToImportedSequenceSamplesFolder, "05_Shadergraph_Example.unity");

    string pathToNewSampleDataMesh = Path.Combine(relativePathToImportedSamples, newVersion, SequencesSamplesFolderName, "ExampleData\\TexturedMesh_Sequence_Sample");
    string pathToNewSampleDataPC = Path.Combine(relativePathToImportedSamples, newVersion, SequencesSamplesFolderName, "ExampleData\\Pointcloud_Sequence_Sample");

    UpdateBasicSample(pathToBasicSceneMesh, pathToNewSampleDataMesh);
    UpdateBasicSample(pathToBasicScenePC, pathToNewSampleDataPC);
    UpdateBasicSample(pathToShadergraphScene, pathToNewSampleDataPC);
    UpdateTimelineSample(pathToTimelineScene, pathToNewSampleDataMesh);
    UpdateAPISample(pathToAPIScene, pathToNewSampleDataMesh);
    RenameSamplePath(Path.Join("Assets", relativePathToImportedSamples, currentVersion), Path.Join("Assets", relativePathToImportedSamples, newVersion));
  }

  bool UpdateBasicSample(string relativePathToScene, string relativeImportedUpgradedSampleDataPath)
  {

    string absolutePath = Path.Combine(Application.dataPath, relativePathToScene);

    //Basic Sample
    try
    {
      EditorSceneManager.OpenScene(absolutePath, OpenSceneMode.Single);
    }

    catch(Exception e)
    {
      Debug.LogError("Could not open scene: " + e.Message);
      return false;
    }

    GeometrySequencePlayer player = (GeometrySequencePlayer)FindFirstObjectByType<GeometrySequencePlayer>();
    if (player.GetRelativeSequencePath() == null)
    {
      Debug.LogError("Could not finde path in basic sample mesh!");
      return false;
    }

    player.SetPath(relativeImportedUpgradedSampleDataPath, GeometrySequenceStream.PathType.RelativeToDataPath);
    EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
    return true;
  }

  bool UpdateTimelineSample(string relativePathToScene, string relativeImportedUpgradedSampleDataPath)
  {
    //Timeline Sample

    string absolutePath = Path.Combine(Application.dataPath, relativePathToScene);

    try
    {
      EditorSceneManager.OpenScene(absolutePath, OpenSceneMode.Single);
    }

    catch
    {
      Debug.LogError("Could not load timeline sample scene!");
      return false;
    }


    PlayableDirector director = (PlayableDirector)FindFirstObjectByType<PlayableDirector>();
    PlayableAsset playable = director.playableAsset;
    TimelineAsset timeline = (TimelineAsset)playable;
    IEnumerable<TimelineClip> clips = timeline.GetRootTrack(1).GetClips();



    foreach (TimelineClip clip in clips)
    {

      GeometrySequenceClip geoClip = (GeometrySequenceClip)clip.asset;

      if (geoClip.relativePath == null)
      {
        Debug.LogError("Could not finde path in timeline Sample!");
        return false;
      }

      geoClip.relativePath = relativeImportedUpgradedSampleDataPath;

    }

    EditorUtility.SetDirty(timeline);
    EditorUtility.SetDirty(playable);
    AssetDatabase.SaveAssets();
    EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
    return true;
  }

  bool UpdateAPISample(string relativePathToScene, string relativeImportedUpgradedSampleDataPath)
  {
    //API Sample

    string absolutePath = Path.Combine(Application.dataPath, relativePathToScene);

    try
    {
      EditorSceneManager.OpenScene(absolutePath, OpenSceneMode.Single);
    }

    catch
    {
      Debug.LogError("Could not load API sample scene!");
      return false;
    }

    GeometrySequenceAPIExample api = (GeometrySequenceAPIExample)FindFirstObjectByType<GeometrySequenceAPIExample>();
    if (api.sequencePath == null)
    {
      Debug.LogError("Could not find path in API Sample!");
      return false;
    }

    api.sequencePath = relativeImportedUpgradedSampleDataPath;
    EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
    return true;
  }

  bool RenameSamplePath(string oldSamplePathRelativeToProject, string newSamplePathRelativeToProject)
  {
    if (Directory.Exists(oldSamplePathRelativeToProject))
    {
      if (oldSamplePathRelativeToProject == newSamplePathRelativeToProject)
        return true;

      string error = AssetDatabase.MoveAsset(oldSamplePathRelativeToProject, newSamplePathRelativeToProject);

      if (error != "")
      {
        Debug.LogError("Could not rename sample directory: " + error + " Maybe you need to close Visual Studio?");
        return false;
      }

    }

    else
    {
      Debug.LogError("Sample directory does not exist");
      return false;
    }

    return true;
  }

  void CopySamples(string absPathToImportedSampleFolder, string absPathToPackageSampleFolder)
  {
    string emptyScene = "Assets\\EmptyScene.unity";
    EditorSceneManager.OpenScene(emptyScene, OpenSceneMode.Single);

    if (!Directory.Exists(absPathToImportedSampleFolder))
    {
      Debug.LogError("Could not find " + absPathToImportedSampleFolder);
      return;
    }

    if (!Directory.Exists(absPathToPackageSampleFolder))
    {
      if (Directory.Exists(Directory.GetParent(absPathToPackageSampleFolder).ToString()))
        Directory.CreateDirectory(absPathToPackageSampleFolder);
      else
      {
        Debug.LogError("Could not find " + absPathToPackageSampleFolder);
        return;
      }
    }

    try
    {
      CopyDirectory(absPathToImportedSampleFolder, absPathToPackageSampleFolder, true);
    }

    catch (Exception e)
    {
      Debug.LogError(e.ToString());
    }
  }

  static void CopyDirectory(string sourceDir, string destinationDir, bool recursive)
  {
    Debug.Log("Copying from: " + sourceDir + " to " + destinationDir);
    // Get information about the source directory
    var dir = new DirectoryInfo(sourceDir);

    // Cache directories before we start copying
    DirectoryInfo[] dirs = dir.GetDirectories();

    //Delete the files in the destination directory
    if (Directory.Exists(destinationDir))
    {
      foreach (string filePath in Directory.GetFiles(destinationDir))
      {
        File.Delete(filePath);
      }
    }

    // Create the destination directory
    DirectoryInfo info = Directory.CreateDirectory(destinationDir);

    // Get the files in the source directory and copy to the destination directory
    foreach (FileInfo file in dir.GetFiles())
    {
      string targetFilePath = Path.Combine(destinationDir, file.Name);
      file.CopyTo(targetFilePath, true);
    }

    // If recursive and copying subdirectories, recursively call this method
    if (recursive)
    {
      foreach (DirectoryInfo subDir in dirs)
      {
        string newDestinationDir = Path.Combine(destinationDir, subDir.Name);
        CopyDirectory(subDir.FullName, newDestinationDir, true);
      }
    }
  }
}